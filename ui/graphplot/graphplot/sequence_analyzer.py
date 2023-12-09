from __future__ import annotations

import collections.abc
import concurrent.futures
import contextlib
import datetime
import threading
import time
from typing import Optional, Self

import polars

from analyza.loading.importers import ShotImporter
from core.session import ExperimentSession, ExperimentSessionMaker
from core.session.sequence import Sequence, Shot, ShotNotFoundError
from util import attrs
from util.concurrent import TaskGroup
from util.itertools import batched
from .data_loading import DataImporter


class SequenceAnalyzer:
    def __init__(self, session_maker: ExperimentSessionMaker) -> None:
        self._monitored_sequences: dict[Sequence, _SequenceInfo] = {}
        self._session_maker = session_maker
        self._must_interrupt = threading.Event()
        self._number_loaded_shots = 0
        self._number_shots_to_load = 0

        self._thread_pool = concurrent.futures.ThreadPoolExecutor()
        self._task_group = TaskGroup(self._thread_pool)
        self._exit_stack = contextlib.ExitStack()
        self._lock = threading.RLock()

    def __enter__(self) -> Self:
        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._thread_pool)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        with self._lock:
            exceptions = []
            for sequence in self.sequences:
                try:
                    self.stop_monitoring_sequence(sequence)
                except Exception as error:
                    exceptions.append(error)
            result = self._exit_stack.__exit__(exc_type, exc_val, exc_tb)
            if exceptions:
                raise ExceptionGroup(
                    "Errors occurred while shutting down sequence analyzer", exceptions
                )
            return result

    @property
    def sequences(self) -> list[Sequence]:
        with self._lock:
            return list(self._monitored_sequences)

    def monitor_sequence(self, sequence: Sequence, data_importer: DataImporter) -> None:
        """Starts to load and analyze data a sequence.

        Args:
            sequence: The sequence to start watching. If it is already monitored by this instance, this will override
                previously loaded data.
            data_importer: A callable used to load and analyze data from a sequence. It will be called on each shot
                when it is loaded, and it should return an iterable of mappings from string to data. The key will be
                used as the name of the columns to construct a dataframe.
        """

        with self._lock:
            self.stop_monitoring_sequence(sequence)

            with self._session_maker() as session:
                stats = sequence.get_stats(session)

            sequence_infos = _SequenceInfo(
                start_date=stats.start_date,
                shot_importer=data_importer,
                dataframe=None,
                number_shots_to_load=stats.number_completed_shots,
                number_imported_shots=0,
                must_interrupt=threading.Event(),
                update_number_shots_future=None,
                loading_future=None,
            )
            self._monitored_sequences[sequence] = sequence_infos
            sequence_infos.loading_future = self._thread_pool.submit(
                self._load_sequence_data, sequence
            )
            sequence_infos.update_number_shots_future = self._thread_pool.submit(
                self._update_number_shots, sequence
            )

    def stop_monitoring_sequence(self, sequence: Sequence) -> None:
        """Stops monitoring a sequence.

        If the sequence is not currently monitored, this method return immediately. Otherwise, it will signal the
        background thread monitoring the sequence to stop and block until this thread finishes.

        Raises:
            The error that happened in the background thread should one have happened.
        """

        with self._lock:
            if sequence in self._monitored_sequences:
                self._monitored_sequences[sequence].must_interrupt.set()
                self._monitored_sequences[sequence].update_number_shots_future.result()
                self._monitored_sequences[sequence].loading_future.result()
                del self._monitored_sequences[sequence]

    def get_sequence_dataframes(self) -> dict[Sequence, Optional[polars.DataFrame]]:
        with self._lock:
            return {
                sequence: info.dataframe
                for sequence, info in self._monitored_sequences.items()
            }

    def get_dataframe(self) -> Optional[polars.DataFrame]:
        dataframes_to_concatenate = [
            dataframe
            for dataframe in self.get_sequence_dataframes().values()
            if (dataframe is not None)
        ]
        if dataframes_to_concatenate:
            return polars.concat(dataframes_to_concatenate)
        else:
            return None

    def _load_sequence_data(self, sequence: Sequence) -> None:
        while not self._monitored_sequences[sequence].must_interrupt.is_set():
            with self._session_maker() as session:
                self._check_sequence_change(sequence, session)
                self._import_new_shots(sequence, session)
            self._monitored_sequences[sequence].must_interrupt.wait(0.5)

    def _update_number_shots(self, sequence: Sequence) -> None:
        while not self._monitored_sequences[sequence].must_interrupt.is_set():
            with self._session_maker() as session:
                stats = sequence.get_stats(session)
                self._monitored_sequences[
                    sequence
                ].number_shots_to_load = stats.number_completed_shots

            self._monitored_sequences[sequence].must_interrupt.wait(0.5)

    def _check_sequence_change(self, sequence: Sequence, session: ExperimentSession):
        start_date = sequence.get_stats(session).start_date
        previous_start_date = self._monitored_sequences[sequence].start_date
        if previous_start_date != start_date:
            self._reset_data_loading(sequence, session)

    def _reset_data_loading(
        self, sequence: Sequence, session: ExperimentSession
    ) -> None:
        stats = sequence.get_stats(session)
        self._monitored_sequences[sequence].start_date = stats.start_date
        self._monitored_sequences[sequence].dataframe = None

    def _import_new_shots(self, sequence: Sequence, session: ExperimentSession) -> None:
        new_shots = self._get_not_yet_imported_shots(sequence, session)

        # Here we process new shots in batch. This has two purposes: the dataframe will slowly increase if we load a
        # sequence with many shots, and it won't just happen once all shots are loaded.
        # We also check if we must exit fast between each batch, in which case we finish this task as soon as possible.
        for shots in batched(new_shots, 5):
            if self._monitored_sequences[sequence].must_interrupt.is_set():
                break
            try:
                self._append_shots_to_dataframe(sequence, shots, session)
            except ShotNotFoundError:
                # It can happen that the sequence is emptied before we managed to process all previous shots.
                # This will raise ShotNotFoundError, in which case we exit this task fast and let the next repetition
                # manage this.
                break
            time.sleep(1e-3)

    def _append_shots_to_dataframe(
        self,
        sequence: Sequence,
        shots: collections.abc.Sequence[Shot],
        session: ExperimentSession,
    ):
        if shots:
            shot_importer = self._monitored_sequences[sequence].shot_importer
            dataframe_to_append = polars.concat(
                shot_importer(shot, session) for shot in shots
            )
        else:
            dataframe_to_append = None

        if (old_dataframe := self._monitored_sequences[sequence].dataframe) is not None:
            if dataframe_to_append is not None:
                self._monitored_sequences[sequence].dataframe = polars.concat(  # type: ignore
                    [old_dataframe, dataframe_to_append]
                )
        else:
            self._monitored_sequences[sequence].dataframe = dataframe_to_append
        self._monitored_sequences[sequence].number_imported_shots += len(shots)

    def _get_not_yet_imported_shots(
        self, sequence: Sequence, session: ExperimentSession
    ) -> list[Shot]:
        shots = sequence.get_shots(session)
        return shots[self._monitored_sequences[sequence].number_imported_shots :]

    def get_progress(self) -> tuple[int, int]:
        total_progress = 0
        total_to_load = 0
        with self._lock:
            for sequence, info in self._monitored_sequences.items():
                progress = (
                    info.number_imported_shots
                    if info.number_imported_shots <= info.number_shots_to_load
                    else info.number_shots_to_load
                )
                total_progress += progress
                total_to_load += info.number_shots_to_load
        return total_progress, total_to_load


@attrs.define
class _SequenceInfo:
    number_shots_to_load: int
    number_imported_shots: int
    start_date: Optional[datetime.datetime]
    shot_importer: ShotImporter
    dataframe: Optional[polars.DataFrame]

    must_interrupt: threading.Event
    loading_future: concurrent.futures.Future
    update_number_shots_future: concurrent.futures.Future

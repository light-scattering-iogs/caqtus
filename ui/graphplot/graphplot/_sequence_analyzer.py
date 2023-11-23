from __future__ import annotations

import collections.abc
import datetime
import threading
from collections.abc import Mapping
from typing import Optional, Any, Self

import pandas

from analyza.loading.importers import ShotImporter
from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.runtime import Sequence, Shot
from sequence.runtime.shot import ShotNotFoundError
from util import attrs
from util.concurrent import BackgroundScheduler
from util.itertools import batched


class SequenceAnalyzer:
    def __init__(self, session_maker: ExperimentSessionMaker) -> None:
        self._sequences: dict[Sequence, _SequenceInfo] = {}
        self._session_maker = session_maker
        self._background_scheduler = BackgroundScheduler(max_workers=1)
        self._must_interrupt = threading.Event()

    def __enter__(self) -> Self:
        self._background_scheduler.__enter__()
        self._background_scheduler.schedule_task(self._update_sequences, 0.5)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # We signal that the background task must be stopped fast. Otherwise, we will have to have that all the data
        # have been loaded from the sequence before we can exit.
        self._must_interrupt.set()
        return self._background_scheduler.__exit__(exc_type, exc_val, exc_tb)

    def is_running(self) -> bool:
        return self._background_scheduler.is_running()

    def monitor_sequence(
        self, sequence: Sequence, shot_importer: ShotImporter[Mapping[str, Any]]
    ) -> None:
        """Starts to load and analyze data a sequence.

        Args:
            sequence: The sequence to start watching. If it is already monitored by this instance, this will override
                previously loaded data.
            shot_importer: A callable used to load and analyze data from a sequence. It will be called on each shot
                when it is loaded, and it should return a mapping from string to data. The key will be used as the name
                of the columns to construct a dataframe.
        """

        with self._session_maker() as session:
            stats = sequence.get_stats(session)
        sequence_infos = _SequenceInfo(
            start_date=stats.start_date,
            shot_importer=shot_importer,
            dataframe=None,
            lock=threading.Lock(),
        )
        if sequence in self._sequences:
            with self._get_sequence_lock(sequence):
                self._sequences[sequence] = sequence_infos
        else:
            self._sequences[sequence] = sequence_infos

    def get_sequence_dataframes(self) -> dict[Sequence, Optional[pandas.DataFrame]]:
        return {sequence: info.dataframe for sequence, info in self._sequences.items()}

    def get_dataframe(self) -> Optional[pandas.DataFrame]:
        dataframes_to_concatenate = [
            dataframe
            for dataframe in self.get_sequence_dataframes().values()
            if (dataframe is not None)
        ]
        if dataframes_to_concatenate:
            return pandas.concat(dataframes_to_concatenate)
        else:
            return None

    def _update_sequences(self) -> None:
        for sequence in self._sequences:
            if self._must_interrupt.is_set():
                break
            self._update_sequence(sequence)

    def _update_sequence(self, sequence: Sequence) -> None:
        with self._session_maker() as session:
            with self._get_sequence_lock(sequence):
                self._check_sequence_change(sequence, session)
                self._import_new_shots(sequence, session)

    def _get_sequence_lock(self, sequence: Sequence) -> threading.Lock:
        return self._sequences[sequence].lock

    def _check_sequence_change(self, sequence: Sequence, session: ExperimentSession):
        start_date = sequence.get_stats(session).start_date
        previous_start_date = self._sequences[sequence].start_date
        if previous_start_date != start_date:
            self._reset_data_loading(sequence, session)

    def _reset_data_loading(
        self, sequence: Sequence, session: ExperimentSession
    ) -> None:
        new_start_date = sequence.get_stats(session).start_date
        self._sequences[sequence].start_date = new_start_date
        self._sequences[sequence].dataframe = None

    def _import_new_shots(self, sequence: Sequence, session: ExperimentSession) -> None:
        new_shots = self._get_not_yet_imported_shots(sequence, session)

        # Here we process new shots in batch. This has two purposes: the dataframe will slowly increase if we load a
        # sequence with many shots, and it won't just happen once all shots are loaded.
        # We also check if we must exit fast between each batch, in which case we finish this task as soon as possible.
        for shots in batched(new_shots, 10):
            if self._must_interrupt.is_set():
                break
            try:
                self._append_shots_to_dataframe(sequence, shots, session)
            except ShotNotFoundError:
                # It can happen that the sequence is emptied before we managed to process all previous shots.
                # This will raise ShotNotFoundError, in which case we exit this task fast and let the next repetition
                # manage this.
                break


    def _append_shots_to_dataframe(
        self,
        sequence: Sequence,
        shots: collections.abc.Sequence[Shot],
        session: ExperimentSession,
    ):
        if shots:
            shot_importer = self._sequences[sequence].shot_importer
            rows = [shot_importer(shot, session) for shot in shots]
            sequence_label = str(sequence.path)
            indices = [(sequence_label, shot.index) for shot in shots]
            index = pandas.MultiIndex.from_tuples(indices, names=["sequence", "shot"])
            dataframe_to_append = pandas.DataFrame(rows, index=index)
        else:
            dataframe_to_append = None

        if (old_dataframe := self._sequences[sequence].dataframe) is not None:
            if dataframe_to_append is not None:
                self._sequences[sequence].dataframe = pandas.concat(
                    [old_dataframe, dataframe_to_append]
                )
        else:
            self._sequences[sequence].dataframe = dataframe_to_append

    def _get_not_yet_imported_shots(
        self, sequence: Sequence, session: ExperimentSession
    ) -> list[Shot]:
        shots = sequence.get_shots(session)
        return shots[self._sequences[sequence].number_imported_shots :]


@attrs.define
class _SequenceInfo:
    start_date: Optional[datetime.datetime]
    shot_importer: ShotImporter
    dataframe: Optional[pandas.DataFrame]
    lock: threading.Lock

    @property
    def number_imported_shots(self) -> int:
        return len(self.dataframe) if (self.dataframe is not None) else 0

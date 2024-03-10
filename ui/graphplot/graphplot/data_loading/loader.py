from __future__ import annotations

import asyncio
import datetime
from typing import Optional

import attrs
import polars
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from core.data_analysis.loading import DataImporter, LoadShotParameters, LoadShotId
from core.session import (
    PureSequencePath,
    ExperimentSessionMaker,
    ExperimentSession,
    Shot,
)
from core.session._return_or_raise import unwrap
from core.session.path_hierarchy import PathNotFoundError
from core.session.sequence_collection import PathIsNotSequenceError
from .loader_ui import Ui_Loader


class DataLoader(QWidget, Ui_Loader):
    def __init__(
        self, shot_loader: DataImporter, session_maker: ExperimentSessionMaker, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setupUi(self)

        self.watchlist: dict[PureSequencePath, SequenceLoadingInfo] = {}
        self.session_maker = session_maker
        self.process_chunk_size = 10
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(1)
        self.shot_loader = shot_loader

    def add_sequence_to_watchlist(self, sequence_path: PureSequencePath):
        if sequence_path not in self.watchlist:
            with self.session_maker() as session:
                stats = unwrap(session.sequences.get_stats(sequence_path))
                start_time = stats.start_time
                number_completed_shots = stats.number_completed_shots
            self.watchlist[sequence_path] = SequenceLoadingInfo(
                start_time=start_time,
                number_completed_shots=number_completed_shots,
                processed_shots=set(),
                dataframe=empty_dataframe(),
            )
            self.sequence_list.addItem(str(sequence_path))

    def get_sequences_data(self) -> dict[PureSequencePath, polars.DataFrame]:
        return {path: info.dataframe for path, info in self.watchlist.items()}

    def remove_sequence_from_watchlist(self, sequence_path: PureSequencePath) -> None:
        """Remove a sequence from the watchlist.

        This method has no effect if the sequence is not in the watchlist.
        """

        if sequence_path in self.watchlist:
            self.watchlist.pop(sequence_path)
            # Need to use reversed to avoid index shifting when removing items
            for item in reversed(
                self.sequence_list.findItems(
                    str(sequence_path), Qt.MatchFlag.MatchExactly
                )
            ):
                self.sequence_list.takeItem(self.sequence_list.row(item))

    def update_progress_bar(self) -> None:
        """Update the progress bar to reflect the number of processed shots."""

        total_shots = sum(
            info.number_completed_shots for info in self.watchlist.values()
        )
        processed_shots = sum(
            len(info.processed_shots) for info in self.watchlist.values()
        )
        self.progress_bar.setMaximum(total_shots)
        self.progress_bar.setValue(processed_shots)

    async def process(self):
        while True:
            await self.single_process()
            await asyncio.sleep(1e-3)

    async def single_process(self):
        # Can't update over the dict watchlist, because it might be updated during the processing
        for sequence_path in list(self.watchlist):
            await self.process_new_shots(sequence_path)

    async def process_new_shots(self, sequence: PureSequencePath) -> None:
        with self.session_maker() as session:
            # Check if the sequence has been reset by comparing the start time
            # of the sequence in the watchlist with the start time of the sequence in the session.
            # If the start time is different, the sequence has been reset, and we clear the processed shots.
            stats_result = await asyncio.to_thread(
                session.sequences.get_stats, sequence
            )
            try:
                stats = unwrap(stats_result)
            except (PathNotFoundError, PathIsNotSequenceError):
                self.remove_sequence_from_watchlist(sequence)
                return
            if stats.start_time != self.watchlist[sequence].start_time:
                self.watchlist[sequence] = SequenceLoadingInfo(
                    start_time=stats.start_time,
                    number_completed_shots=stats.number_completed_shots,
                    processed_shots=set(),
                    dataframe=empty_dataframe(),
                )
                return
            result = await asyncio.to_thread(session.sequences.get_shots, sequence)
            try:
                shots = unwrap(result)
            except (PathNotFoundError, PathIsNotSequenceError):
                self.remove_sequence_from_watchlist(sequence)
                return

            processed_shots = self.watchlist[sequence].processed_shots
            new_shots = sorted(
                (shot for shot in shots if shot.index not in processed_shots),
                key=lambda s: s.index,
            )
            for shot in list(new_shots)[: self.process_chunk_size]:
                await self.process_shot(shot, session)
            self.update_progress_bar()

    async def process_shot(self, shot: Shot, session: ExperimentSession) -> None:
        new_data = await asyncio.to_thread(self.shot_loader, shot, session)
        processing_info = self.watchlist[shot.sequence.path]
        total_data = processing_info.dataframe
        concatenated = polars.concat([total_data, new_data])
        processing_info.dataframe = concatenated
        processing_info.processed_shots.add(shot.index)


@attrs.define
class SequenceLoadingInfo:
    start_time: Optional[datetime.datetime]
    number_completed_shots: int
    processed_shots: set[int]
    dataframe: polars.DataFrame


def empty_dataframe() -> polars.DataFrame:
    return polars.DataFrame()

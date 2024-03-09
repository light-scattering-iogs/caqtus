from __future__ import annotations

import asyncio
import datetime
from typing import Optional

import attrs
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from core.session import PureSequencePath, ExperimentSessionMaker
from core.session._return_or_raise import unwrap
from core.session.path_hierarchy import PathNotFoundError
from core.session.sequence_collection import PathIsNotSequenceError
from .loader_ui import Ui_Loader


class DataLoader(QWidget, Ui_Loader):
    def __init__(
        self, session_maker: ExperimentSessionMaker, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setupUi(self)

        self.watchlist: dict[PureSequencePath, SequenceLoadingInfo] = {}
        self.session_maker = session_maker
        self.process_chunk_size = 10
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(1)

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
            )
            self.sequence_list.addItem(str(sequence_path))

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
            await asyncio.sleep(10e-3)

    async def single_process(self):
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
                )
                return
            result = await asyncio.to_thread(session.sequences.get_shots, sequence)
            try:
                shots = unwrap(result)
            except (PathNotFoundError, PathIsNotSequenceError):
                self.remove_sequence_from_watchlist(sequence)
                return

            processed_shots = self.watchlist[sequence].processed_shots
            new_shots = sorted(set(shot.index for shot in shots) - processed_shots)
            for shot_index in list(new_shots)[: self.process_chunk_size]:
                await self.process_shot(sequence, shot_index)
            self.update_progress_bar()

    async def process_shot(self, sequence: PureSequencePath, shot_index: int) -> None:
        self.watchlist[sequence].processed_shots.add(shot_index)


@attrs.define
class SequenceLoadingInfo:
    start_time: Optional[datetime.datetime]
    number_completed_shots: int
    processed_shots: set[int]

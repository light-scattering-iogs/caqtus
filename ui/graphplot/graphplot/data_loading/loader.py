from __future__ import annotations

import datetime
from typing import Optional

import attrs
from PySide6.QtWidgets import QWidget

from core.session import PureSequencePath, ExperimentSessionMaker
from core.session._return_or_raise import unwrap
from .loader_ui import Ui_Loader


class DataLoader(QWidget, Ui_Loader):
    def __init__(
        self, session_maker: ExperimentSessionMaker, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setupUi(self)

        self.watchlist: dict[PureSequencePath, SequenceLoadingInfo] = {}
        self.session_maker = session_maker

    def add_sequence_to_watchlist(self, sequence_path: PureSequencePath):
        if sequence_path not in self.watchlist:
            with self.session_maker() as session:
                stats = unwrap(session.sequences.get_stats(sequence_path))
                start_time = stats.start_time
                number_completed_shots = stats.number_completed_shots
            self.watchlist[sequence_path] = SequenceLoadingInfo(
                start_time=start_time,
                number_completed_shots=number_completed_shots,
                number_processed_shots=0,
            )
            self.sequence_list.addItem(str(sequence_path))


@attrs.define
class SequenceLoadingInfo:
    start_time: Optional[datetime.datetime]
    number_completed_shots: int
    number_processed_shots: int

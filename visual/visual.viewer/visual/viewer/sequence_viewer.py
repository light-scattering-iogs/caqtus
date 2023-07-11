from typing import Callable, Any, Optional

import pandas
from PyQt6.QtCore import pyqtSignal, QObject

from visual.sequence_watcher import (
    DataframeSequenceWatcher,
)
from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.runtime import Sequence, Shot
from visual.sequence_watcher.sequence_watcher import (
    DEFAULT_WATCH_INTERVAL,
    DEFAULT_CHUNK_SIZE,
)


class SignalingSequenceWatcher(DataframeSequenceWatcher, QObject):
    new_shots_processed = pyqtSignal(list)

    def __init__(
        self,
        sequence: Sequence,
        importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
        session_maker: Optional[ExperimentSessionMaker] = None,
        watch_interval: float = DEFAULT_WATCH_INTERVAL,
        chunk_size: Optional[int] = DEFAULT_CHUNK_SIZE,
        *args,
        **kwargs
    ):
        super().__init__(
            sequence=sequence,
            importer=importer,
            session_maker=session_maker,
            watch_interval=watch_interval,
            chunk_size=chunk_size,
        )
        QObject.__init__(self, *args, **kwargs)

    def process_shots(self, new_shots: list[Shot]) -> pandas.Index:
        """Add new shots to the dataframe and emit a signal with the new shots"""

        index = super().process_shots(new_shots)
        self.new_shots_processed.emit(new_shots)
        return index

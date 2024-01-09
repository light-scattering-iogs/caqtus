from typing import Optional

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QTableView

from condetrol.timelanes_editor.model import TimeLanesModel
from core.session.shot import TimeLanes


class TimeLanesEditor(QTableView):
    time_lanes_changed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._read_only: bool = False
        self._model = TimeLanesModel(self)
        self.setModel(self._model)

    def get_time_lanes(self) -> TimeLanes:
        return self._model.get_timelanes()

    def set_time_lanes(self, time_lanes: TimeLanes) -> None:
        self._model.set_timelanes(time_lanes)

    def set_read_only(self, read_only: bool) -> None:
        raise NotImplementedError

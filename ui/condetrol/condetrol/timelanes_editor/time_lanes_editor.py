from typing import Optional

from PyQt6.QtCore import pyqtSignal, QObject, Qt, QModelIndex
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QTableView, QMenu

from core.session.shot import TimeLanes
from .default_lane_model_factory import default_lane_model_factory
from .model import TimeLanesModel


class TimeLanesEditor(QTableView):
    time_lanes_changed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._read_only: bool = False
        self._model = TimeLanesModel(default_lane_model_factory, self)
        self.setModel(self._model)

        self.horizontalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.horizontalHeader().customContextMenuRequested.connect(
            self.show_steps_context_menu
        )

    def get_time_lanes(self) -> TimeLanes:
        return self._model.get_timelanes()

    def set_time_lanes(self, time_lanes: TimeLanes) -> None:
        self._model.set_timelanes(time_lanes)

    def set_read_only(self, read_only: bool) -> None:
        raise NotImplementedError

    def show_steps_context_menu(self, pos):
        menu = QMenu(self.horizontalHeader())

        index = self.horizontalHeader().logicalIndexAt(pos.x())
        if index == -1:
            add_step_action = QAction("Add step")
            menu.addAction(add_step_action)
            add_step_action.triggered.connect(
                lambda: self._model.insertColumn(
                    self._model.columnCount(), QModelIndex()
                )
            )
        elif 0 <= index < self.model().columnCount():
            add_step_before_action = QAction("Insert step before")
            menu.addAction(add_step_before_action)
            add_step_before_action.triggered.connect(
                lambda: self._model.insertColumn(index, QModelIndex())
            )

            add_step_after_action = QAction("Insert step after")
            menu.addAction(add_step_after_action)
            add_step_after_action.triggered.connect(
                lambda: self._model.insertColumn(index + 1, QModelIndex())
            )

            remove_step_action = QAction("Remove")
            menu.addAction(remove_step_action)
            remove_step_action.triggered.connect(
                lambda: self._model.removeColumn(index, QModelIndex())
            )
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

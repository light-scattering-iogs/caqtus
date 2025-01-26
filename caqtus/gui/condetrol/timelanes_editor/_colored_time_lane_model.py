from __future__ import annotations

import abc
from typing import Optional, Any

from PySide6.QtCore import (
    QObject,
    Qt,
    QSettings,
)
from PySide6.QtGui import QAction, QBrush, QColor, QUndoStack
from PySide6.QtWidgets import QMenu, QColorDialog

import caqtus.gui.qtutil.qabc as qabc
from caqtus.types.timelane import TimeLane
from ._time_lane_model import TimeLaneModel


class ColoredTimeLaneModel[L: TimeLane](TimeLaneModel[L], metaclass=qabc.QABCMeta):
    """A time lane model that can be colored.

    Instances of this class can be used to color the cells in a lane.
    They have the attribute :attr:`_brush` that is optionally a :class:`QBrush` that
    can be used to color the cells in the lane.
    """

    def __init__(
        self,
        name: str,
        lane: L,
        parent: Optional[QObject] = None,
    ):
        super().__init__(name, lane, parent)
        self._brush: Optional[QBrush] = None

        color = QSettings().value(f"lane color/{self.name()}", None)
        if color is not None:
            self._brush = QBrush(color)
        else:
            self._brush = None

    @abc.abstractmethod
    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Returns its brush for the `Qt.ItemDataRole.ForegroundRole` role."""

        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._brush

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._brush
        return super().headerData(section, orientation, role)

    def get_header_context_actions(self) -> list[QAction | QMenu]:
        action = QAction("Change color")
        action.triggered.connect(lambda: self._change_color())
        return [action]

    def _change_color(self):
        if self._brush is None:
            color = QColorDialog.getColor(title=f"Select color for {self.name()}")
        else:
            color = QColorDialog.getColor(
                self._brush.color(), title=f"Select color for {self.name()}"
            )
        if color.isValid():
            self.setHeaderData(
                0, Qt.Orientation.Horizontal, color, Qt.ItemDataRole.ForegroundRole
            )

    def setHeaderData(self, section, orientation, value, role=Qt.ItemDataRole.EditRole):
        change = False
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.ForegroundRole
        ):
            if isinstance(value, QColor):
                self._brush = QBrush(value)
                settings = QSettings()
                settings.setValue(f"lane color/{self.name()}", value)
                change = True
            elif value is None:
                self._brush = None
                settings = QSettings()
                settings.remove(f"lane color/{self.name()}")
                change = True
        if change:
            self.headerDataChanged.emit(orientation, section, section)
            return True

        return super().setHeaderData(section, orientation, value, role)

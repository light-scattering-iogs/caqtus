import copy
from typing import Optional, Any, assert_never

from PyQt6.QtCore import QObject, QModelIndex, Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from core.session.shot.timelane import AnalogTimeLane, Ramp
from core.types.expression import Expression
from .model import TimeLaneModel


class AnalogTimeLaneModel(TimeLaneModel[AnalogTimeLane, None]):
    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(name, parent)
        self._lane = AnalogTimeLane([Expression("...")])
        self._brush = None

    def set_lane(self, lane: AnalogTimeLane) -> None:
        self.beginResetModel()
        self._lane = copy.deepcopy(lane)
        self.endResetModel()

    def get_lane(self) -> AnalogTimeLane:
        return copy.deepcopy(self._lane)

    def set_display_options(self, options) -> None:
        pass

    def rowCount(self, parent: QModelIndex = QModelIndex()):
        return len(self._lane)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        value = self._lane[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(value, Expression):
                return str(value)
            elif isinstance(value, Ramp):
                return "\u279F"
            else:
                assert_never(value)
        elif role == Qt.ItemDataRole.EditRole:
            if isinstance(value, Expression):
                return str(value)
            return None
        elif role == Qt.ItemDataRole.ForegroundRole:
            return self._brush
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        else:
            return None

    def setData(
        self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole
    ):
        print(index.row())
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            start, stop = self._lane.get_bounds(index.row())
            if isinstance(value, str):
                self._lane[start:stop] = Expression(value)
                self.dataChanged.emit(index, index)
                return True
            elif isinstance(value, Ramp):
                self._lane[start:stop] = value
                self.dataChanged.emit(index, index)
                return True
            else:
                raise TypeError(f"Invalid type for value: {type(value)}")
        return False

    def insertRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row <= len(self._lane)):
            return False
        self.beginInsertRows(parent, row, row)
        self._lane.insert(row, Expression("..."))
        self.endInsertRows()
        return True

    def removeRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row < len(self._lane)):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._lane[row]
        self.endRemoveRows()
        return True

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        if not index.isValid():
            return []
        break_span_action = QAction("Break span")
        break_span_action.triggered.connect(lambda: self.break_span(index))
        cell_type_menu = QMenu("Cell type")
        value = self._lane[index.row()]
        expr_action = cell_type_menu.addAction("expression")
        if isinstance(value, Expression):
            expr_action.setCheckable(True)
            expr_action.setChecked(True)
        else:
            expr_action.triggered.connect(
                lambda: self.setData(index, "...", Qt.ItemDataRole.EditRole)
            )
        ramp_action = cell_type_menu.addAction("ramp")
        if isinstance(value, Ramp):
            ramp_action.setCheckable(True)
            ramp_action.setChecked(True)
        else:
            ramp_action.triggered.connect(
                lambda: self.setData(index, Ramp(), Qt.ItemDataRole.EditRole)
            )

        return [break_span_action, cell_type_menu]

    def span(self, index) -> QSize:
        start, stop = self._lane.get_bounds(index.row())
        if index.row() == start:
            return QSize(1, stop - start)
        else:
            return QSize(1, 1)

    def break_span(self, index: QModelIndex) -> bool:
        start, stop = self._lane.get_bounds(index.row())
        value = self._lane[index.row()]
        for i in range(start, stop):
            self._lane[i] = value
            self.dataChanged.emit(self.index(i), self.index(i))
        return True

    def merge_cells(self, start: int, stop: int) -> None:
        value = self._lane[start]
        self._lane[start:stop+1] = value
        self.dataChanged.emit(self.index(start), self.index(stop - 1))

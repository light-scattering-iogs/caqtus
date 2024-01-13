import copy
from typing import Optional, Any, assert_never

from PyQt6.QtCore import QObject, QModelIndex, Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from core.session.shot import DigitalTimeLane
from core.types.expression import Expression
from .model import TimeLaneModel


class DigitalTimeLaneModel(TimeLaneModel[DigitalTimeLane, None]):
    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(name, parent)
        self._lane = DigitalTimeLane([(False, 1)])

    def set_lane(self, lane: DigitalTimeLane) -> None:
        self.beginResetModel()
        self._lane = copy.deepcopy(lane)
        self.endResetModel()

    def get_lane(self) -> DigitalTimeLane:
        return copy.deepcopy(self._lane)

    def set_display_options(self, options) -> None:
        pass

    def rowCount(self, parent: QModelIndex = QModelIndex()):
        return len(self._lane)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            value = self._lane[index.row()]
            if isinstance(value, bool):
                return value
            elif isinstance(value, Expression):
                return str(value)
            else:
                assert_never(value)
        else:
            return None

    def setData(
        self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole
    ):
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            start, stop = self._lane.get_bounds(index.row())
            if isinstance(value, bool):
                self._lane[start:stop] = value
                self.dataChanged.emit(index, index)
                return True
            elif isinstance(value, str):
                self._lane[start:stop] = Expression(value)
                self.dataChanged.emit(index, index)
                return True
            else:
                raise TypeError(f"Invalid type for value: {type(value)}")
        return False

    def insertRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row <= len(self._lane)):
            return False
        self.beginInsertRows(parent, row, row)
        self._lane.insert(row, False)
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
        cell_type_menu = QMenu("Cell type")
        value = self._lane[index.row()]
        bool_action = cell_type_menu.addAction("on/off")
        if isinstance(value, bool):
            bool_action.setCheckable(True)
            bool_action.setChecked(True)
        else:
            bool_action.triggered.connect(
                lambda: self.setData(index, False, Qt.ItemDataRole.EditRole)
            )
        expr_action = cell_type_menu.addAction("expression")
        if isinstance(value, Expression):
            expr_action.setCheckable(True)
            expr_action.setChecked(True)
        else:
            expr_action.triggered.connect(
                lambda: self.setData(
                    index, str(Expression("...")), Qt.ItemDataRole.EditRole
                )
            )

        return [cell_type_menu]

    def span(self, index) -> QSize:
        start, stop = self._lane.get_bounds(index.row())
        if index.row() == start:
            return QSize(1, stop - start)
        else:
            return QSize(1, 0)

import copy
from typing import Optional, Any

from PyQt6.QtCore import QObject, QModelIndex, Qt

from core.session.shot import DigitalTimeLane
from .model import TimeLaneModel


class DigitalTimeLaneModel(TimeLaneModel[DigitalTimeLane, None]):
    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(name, parent)
        self._lane = DigitalTimeLane()

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
            return self._lane[index.row()]
        else:
            return None

    def setData(
        self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole
    ):
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            if not isinstance(value, bool):
                raise TypeError(f"Expected bool, got {type(value)}")
            self._lane[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
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

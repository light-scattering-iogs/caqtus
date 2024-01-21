import copy
from typing import Optional, Any, assert_never

from PyQt6.QtCore import QObject, QModelIndex, Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from core.session.shot.timelane import CameraTimeLane, TakePicture
from core.types.image import ImageLabel
from .model import TimeLaneModel
from ..icons import get_icon


class CameraTimeLaneModel(TimeLaneModel[CameraTimeLane, None]):
    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(name, parent)
        self._lane = CameraTimeLane.from_sequence([None])
        self._brush = None

    def set_lane(self, lane: CameraTimeLane) -> None:
        self.beginResetModel()
        self._lane = copy.deepcopy(lane)
        self.endResetModel()

    def get_lane(self) -> CameraTimeLane:
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
            if isinstance(value, TakePicture):
                return value.picture_name
            elif value is None:
                return None
            else:
                assert_never(value)
        elif role == Qt.ItemDataRole.EditRole:
            if isinstance(value, TakePicture):
                return value.picture_name
            elif value is None:
                return ""
            else:
                assert_never(value)
        elif role == Qt.ItemDataRole.ForegroundRole:
            return self._brush
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        elif role == Qt.ItemDataRole.DecorationRole:
            if isinstance(value, TakePicture):
                return get_icon("camera")
        else:
            return None

    def setData(
        self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole
    ):
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            start, stop = self._lane.get_bounds(index.row())
            if isinstance(value, str):
                if value == "":
                    self._lane[start:stop] = None
                else:
                    self._lane[start:stop] = TakePicture(ImageLabel(value))
                self.dataChanged.emit(index, index)
                return True
            else:
                raise TypeError(f"Invalid type for value: {type(value)}")
        return False

    def insertRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row <= len(self._lane)):
            return False
        self.beginInsertRows(parent, row, row)
        self._lane.insert(row, None)
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
        return []

    def span(self, index) -> QSize:
        start, stop = self._lane.get_bounds(index.row())
        if index.row() == start:
            return QSize(1, stop - start)
        else:
            return QSize(1, 0)

from typing import Optional, Any, assert_never

from PySide6.QtCore import QObject, QModelIndex, Qt

from core.session.shot.timelane import CameraTimeLane, TakePicture
from core.types.data import DataLabel
from core.types.image import ImageLabel
from .model import TimeLaneModel
from ..icons import get_icon


class CameraTimeLaneModel(TimeLaneModel[CameraTimeLane, None]):
    def __init__(self, name: str, parent: Optional[QObject] = None):
        lane = CameraTimeLane([None])
        super().__init__(name, lane, parent)
        self._brush = None

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
                elif isinstance(value, str):
                    self._lane[start:stop] = TakePicture(ImageLabel(DataLabel(value)))
                else:
                    raise TypeError(f"Invalid type for value: {type(value)}")
                self.dataChanged.emit(index, index)
                return True
            else:
                raise TypeError(f"Invalid type for value: {type(value)}")
        return False

    def insertRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        return self.insert_value(row, None)

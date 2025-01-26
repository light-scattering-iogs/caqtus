from typing import Optional, Any, assert_never

from PySide6.QtCore import QObject, QModelIndex, Qt, QPersistentModelIndex
from PySide6.QtGui import QPalette, QUndoStack

from caqtus.gui.condetrol._icons import get_icon
from caqtus.types.data import DataLabel
from caqtus.types.image import ImageLabel
from caqtus.types.timelane import CameraTimeLane, TakePicture
from .._time_lane_model import TimeLaneModel

_DEFAULT_INDEX = QModelIndex()


class CameraTimeLaneModel(TimeLaneModel[CameraTimeLane]):
    # ruff: noqa: N802
    def __init__(self, name: str, parent: Optional[QObject] = None):
        lane = CameraTimeLane([None])
        super().__init__(name, lane, parent)
        self._brush = None
        palette = QPalette()
        color = palette.text().color()
        self._icon = get_icon("camera", color=color)

    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        value = self.lane_value(index.row())
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
                return self._icon
        else:
            return None

    def setData(self, index, value: Any, role: int = Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            assert isinstance(value, str)

            if value == "":
                new_value = None
            else:
                new_value = TakePicture(ImageLabel(DataLabel(value)))

            return self.set_lane_value(index.row(), new_value)

        return False

    def insertRow(
        self, row, parent: QModelIndex | QPersistentModelIndex = _DEFAULT_INDEX
    ) -> bool:
        return self.insert_lane_value(row, None)

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QColor, QIcon

from camera_lane.configuration import CameraLane, TakePicture
from experiment.configuration import ExperimentConfig
from lane.model import LaneModel
from sequencer.configuration import ChannelSpecialPurpose


class CameraLaneModel(LaneModel[CameraLane]):
    def __init__(
        self, lane: CameraLane, experiment_config: ExperimentConfig, *args, **kwargs
    ):
        super().__init__(lane, experiment_config, *args, **kwargs)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        camera_action: CameraLane = self.lane[index.row()]
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if camera_action is None:
                return ""
            elif isinstance(camera_action, TakePicture):
                return camera_action.picture_name
        elif role == Qt.ItemDataRole.DecorationRole:
            if isinstance(camera_action, TakePicture):
                return QIcon("icons:camera-lens.png")
        elif role == Qt.ItemDataRole.TextColorRole:
            try:
                color = self._experiment_config.get_color(
                    ChannelSpecialPurpose(purpose=self.lane.name)
                )
            except ValueError:
                return QColor.fromRgb(0, 0, 0)
            else:
                if color is not None:
                    return QColor.fromRgb(*color.as_rgb_tuple(alpha=False))

    def setData(self, index: QModelIndex, value: str, role: int = Qt.ItemDataRole.EditRole) -> bool:
        edit = False
        if role == Qt.ItemDataRole.EditRole:
            if value == "":
                self.lane[index.row()] = None
                edit = True
            elif isinstance(value, str):
                value = TakePicture(picture_name=value)
                self.lane[index.row()] = value
                edit = True
        return edit

    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row)
        self.lane.insert(row, None)
        self.endInsertRows()
        return True

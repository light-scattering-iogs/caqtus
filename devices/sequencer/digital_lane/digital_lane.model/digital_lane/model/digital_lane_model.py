from typing import Optional

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QColor, QBrush

from digital_lane.configuration import DigitalLane, Blink
from experiment.configuration import ExperimentConfig
from lane.configuration import Lane
from lane.model import LaneModel


class DigitalLaneModel(LaneModel):
    def __init__(
        self, lane: DigitalLane, experiment_config: ExperimentConfig, *args, **kwargs
    ):
        super().__init__(lane, experiment_config, *args, **kwargs)
        self._lane_brush = _get_color(self.lane, self.experiment_config)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        cell_value = self.lane[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(cell_value, Blink):
                return str(cell_value)
        elif role == Qt.ItemDataRole.EditRole:
            return cell_value
        elif role == Qt.ItemDataRole.BackgroundRole:
            if isinstance(cell_value, bool):
                if cell_value:
                    return self._lane_brush
                else:
                    return None
            elif isinstance(cell_value, Blink):
                return self._lane_brush
            else:
                raise NotImplementedError(
                    f"BackgroundRole not implemented for {type(cell_value)}"
                )
        elif role == Qt.ItemDataRole.ForegroundRole:
            return QBrush(QColor.fromRgb(0, 0, 0))

    def setData(
        self, index: QModelIndex, value: bool, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            self.lane[index.row()] = value
            return True
        else:
            return False

    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row)
        self.lane.insert(row, False)
        self.endInsertRows()
        return True


def _get_color(lane: Lane, experiment_config: ExperimentConfig) -> Optional[QBrush]:
    try:
        color = experiment_config.get_color(lane.name)
    except ValueError:
        return QBrush(QColor.fromRgb(0, 0, 0))
    else:
        if color is not None:
            return QBrush(QColor.fromRgb(*color.as_rgb_tuple(alpha=False)))
        else:
            return None

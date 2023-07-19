from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QColor

from experiment.configuration import ExperimentConfig
from expression import Expression
from analog_lane.configuration import AnalogLane, Ramp
from lane.model import LaneModel
from settings_model import YAMLSerializable


class AnalogLaneModel(LaneModel[AnalogLane]):
    def __init__(
        self, lane: AnalogLane, experiment_config: ExperimentConfig, *args, **kwargs
    ):
        super().__init__(lane, experiment_config, *args, **kwargs)

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            value = self.lane[index.row()]
            if isinstance(value, Expression):
                return value.body
            elif isinstance(value, Ramp):
                if role == Qt.ItemDataRole.DisplayRole:
                    return "\u279F"
                elif role == Qt.ItemDataRole.EditRole:
                    return YAMLSerializable.to_yaml(value)[:-4]
        elif role == Qt.ItemDataRole.TextColorRole:
            try:
                color = self._experiment_config.get_color(self.lane.name)
            except ValueError:
                return QColor.fromRgb(0, 0, 0)
            else:
                if color is not None:
                    return QColor.fromRgb(*color.as_rgb_tuple())
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

    def setData(self, index: QModelIndex, value: str, role: int = ...) -> bool:
        edit = False
        if role == Qt.ItemDataRole.EditRole:
            if YAMLSerializable.is_tag(value):
                try:
                    value = YAMLSerializable.load(value)
                except Exception as error:
                    raise ValueError(f"Invalid tag: {value}") from error
                if isinstance(value, Ramp):
                    self.lane[index.row()] = value
                    edit = True
            else:
                value = Expression(value)
                self.lane[index.row()] = value
                edit = True
            return edit

    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row)
        self.lane.insert(row, Expression("..."))
        self.endInsertRows()
        return True

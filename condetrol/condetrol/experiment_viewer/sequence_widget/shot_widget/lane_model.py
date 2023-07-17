from functools import singledispatch
from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt, QSize
from PyQt6.QtGui import QColor, QIcon, QBrush

from experiment.configuration import ExperimentConfig
from expression import Expression
from sequence.configuration import (
    Lane,
    Ramp,
    DigitalLane,
    AnalogLane,
    CameraLane,
    TakePicture,
    Blink,
)
from sequencer.configuration import ChannelSpecialPurpose
from settings_model import YAMLSerializable


@singledispatch
def get_lane_model(lane: Lane, experiment_config: ExperimentConfig):
    raise NotImplementedError(
        f"get_lane_model not implemented for {type(lane)} and {type(experiment_config)}"
    )


@get_lane_model.register
def _(digital_lane: DigitalLane, experiment_config: ExperimentConfig):
    return DigitalLaneModel(digital_lane, experiment_config)


@get_lane_model.register
def _(analog_lane: AnalogLane, experiment_config: ExperimentConfig):
    return AnalogLaneModel(analog_lane, experiment_config)


@get_lane_model.register
def _(camera_lane: CameraLane, experiment_config: ExperimentConfig):
    return CameraLaneModel(camera_lane, experiment_config)


def create_new_lane(
    number_steps: int,
    lane_type: type[Lane],
    name: str,
    experiment_config: ExperimentConfig,
) -> Lane:
    if lane_type == DigitalLane:
        new_lane = DigitalLane(
            name=name,
            values=tuple(False for _ in range(number_steps)),
            spans=tuple(1 for _ in range(number_steps)),
        )
    elif lane_type == AnalogLane:
        new_lane = AnalogLane(
            name=name,
            values=tuple(Expression("...") for _ in range(number_steps)),
            spans=tuple(1 for _ in range(number_steps)),
            units=experiment_config.get_input_units(name),
        )
    elif lane_type == CameraLane:
        new_lane = CameraLane(
            name=name,
            values=(None,) * number_steps,
            spans=(1,) * number_steps,
        )
    else:
        raise NotImplementedError(f"create_new_lane not implemented for {lane_type}")

    return new_lane


class LaneModel(QAbstractListModel):
    def __init__(
        self, lane: Lane, experiment_config: ExperimentConfig, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.lane = lane
        self.experiment_config = experiment_config

    @property
    def lane(self):
        return self._lane

    @lane.setter
    def lane(self, lane: Lane):
        self.beginResetModel()
        self._lane = lane
        self.endResetModel()

    @property
    def experiment_config(self):
        return self._experiment_config

    @experiment_config.setter
    def experiment_config(self, experiment_config: ExperimentConfig):
        self.beginResetModel()
        self._experiment_config = experiment_config
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.lane)

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = ...
    ) -> str:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.lane.name
            else:
                return str(section)

    def span(self, index: QModelIndex) -> QSize:
        return QSize(self.lane.spans[index.row()], 1)

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginRemoveRows(parent, row, row)
        self.lane.remove(row)
        self.endRemoveRows()
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if self.lane.spans[index.row()] > 0:
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemIsSelectable
            )
        else:
            return Qt.ItemFlag.ItemIsSelectable

    def merge(self, start, stop):
        self.beginResetModel()
        self.lane.merge(start, stop)
        self.endResetModel()

    def break_up(self, start, stop):
        self.beginResetModel()
        self.lane.break_(start, stop)
        self.endResetModel()


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

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
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

class AnalogLaneModel(LaneModel):
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

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginInsertRows(parent, row, row)
        self.lane.insert(row, Expression("..."))
        self.endInsertRows()
        return True


class CameraLaneModel(LaneModel):
    def __init__(
        self, lane: CameraLane, experiment_config: ExperimentConfig, *args, **kwargs
    ):
        super().__init__(lane, experiment_config, *args, **kwargs)

    def data(self, index: QModelIndex, role: int = ...):
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

    def setData(self, index: QModelIndex, value: str, role: int = ...) -> bool:
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

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginInsertRows(parent, row, row)
        self.lane.insert(row, None)
        self.endInsertRows()
        return True

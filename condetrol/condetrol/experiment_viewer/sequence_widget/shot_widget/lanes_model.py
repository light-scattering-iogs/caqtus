import logging
from itertools import groupby
from typing import Type, Iterable

from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    QSize,
)
from PyQt6.QtGui import QColor, QIcon

from experiment.configuration import ExperimentConfig, ChannelSpecialPurpose
from expression import Expression
from sequence.configuration import (
    DigitalLane,
    AnalogLane,
    Lane,
    CameraLane,
    TakePicture,
    CameraAction,
    Ramp,
)
from settings_model import YAMLSerializable

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class LanesModel(QAbstractTableModel):
    def __init__(
        self, lanes: list[Lane], experiment_config: ExperimentConfig, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._lanes = lanes
        self._experiment_config = experiment_config

    @property
    def lanes(self):
        return self._lanes

    @lanes.setter
    def lanes(self, lanes: list[Lane]):
        self.beginResetModel()
        self._lanes = lanes
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
        return len(self._lanes)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        length = len(self._lanes[0])
        assert all(len(lane) == length for lane in self._lanes)
        return length

    def data(self, index: QModelIndex, role: int = ...):
        return self.get_lane_data(self._lanes[index.row()], index.column(), role)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return f"Step {section}"
            elif orientation == Qt.Orientation.Vertical:
                return self._lanes[section].name

    def get_lane_data(self, lane: Lane, step: int, role: int = ...):
        if isinstance(lane, DigitalLane):
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                return lane[step]
        elif isinstance(lane, AnalogLane):
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                value = lane[step]
                if isinstance(value, Expression):
                    return value.body
                elif isinstance(value, Ramp):
                    if role == Qt.ItemDataRole.DisplayRole:
                        return "\u279F"
                    elif role == Qt.ItemDataRole.EditRole:
                        return YAMLSerializable.to_yaml(value)[:-4]
            elif role == Qt.ItemDataRole.TextColorRole:
                try:
                    color = self._experiment_config.get_color(lane.name)
                except ValueError:
                    return QColor.fromRgb(0, 0, 0)
                else:
                    if color is not None:
                        return QColor.fromRgb(*color.as_rgb_tuple())
            elif role == Qt.ItemDataRole.TextAlignmentRole:
                if lane.spans[step] > 1 or isinstance(lane[step], Ramp):
                    return Qt.AlignmentFlag.AlignCenter
                else:
                    return Qt.AlignmentFlag.AlignLeft
        elif isinstance(lane, CameraLane):
            camera_action = lane[step]
            if isinstance(camera_action, TakePicture):
                if (
                    role == Qt.ItemDataRole.DisplayRole
                    or role == Qt.ItemDataRole.EditRole
                ):
                    return camera_action.picture_name
                elif role == Qt.ItemDataRole.DecorationRole:
                    return QIcon(":/icons/camera-icon")
                elif role == Qt.ItemDataRole.TextColorRole:
                    try:
                        color = self._experiment_config.get_color(
                            ChannelSpecialPurpose(purpose=lane.name)
                        )
                    except ValueError:
                        return QColor.fromRgb(0, 0, 0)
                    else:
                        if color is not None:
                            return QColor.fromRgb(*color.as_rgb_tuple())

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            return self.set_lane_data(
                self._lanes[index.row()], index.column(), value, role
            )

    def set_lane_data(self, lane: Lane, step: int, value, role: int) -> bool:
        edit = False
        if isinstance(lane, AnalogLane):
            if YAMLSerializable.is_tag(value):
                value = YAMLSerializable.load(value)
                if isinstance(value, Ramp):
                    lane[step] = value
                    edit = True
            else:
                value = Expression(value)
                lane[step] = value
                edit = True
        elif isinstance(lane, DigitalLane):
            lane[step] = value
            edit = True
        elif isinstance(lane, CameraLane):
            if value is None or isinstance(value, CameraAction):
                lane[step] = value
                edit = True
            elif isinstance(value, str) and isinstance(cell := lane[step], TakePicture):
                cell.picture_name = value
                edit = True
        return edit

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        f = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        lane = self._lanes[index.row()]
        editable = True
        if isinstance(lane, CameraLane):
            if self.data(index, Qt.ItemDataRole.EditRole) is None:
                editable = False
        if editable:
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def span(self, index: QModelIndex) -> "QSize":
        return QSize(self._lanes[index.row()].spans[index.column()], 1)

    def insertColumn(self, column: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginInsertColumns(parent, column, column)
        for lane in self._lanes:
            if isinstance(lane, DigitalLane):
                lane.insert(column, False)
            elif isinstance(lane, AnalogLane):
                lane.insert(column, Expression("..."))
            elif isinstance(lane, CameraLane):
                lane.insert(column, None)
        self.endInsertColumns()
        return True

    def removeColumn(self, column: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginRemoveColumns(parent, column, column)
        for lane in self._lanes:
            lane.remove(column)
        self.endRemoveColumns()
        return True

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginRemoveRows(parent, row, row)
        self._lanes.pop(row)
        self.endRemoveRows()
        return True

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginRemoveRows(parent, row, row + count - 1)
        for _ in range(count):
            self._lanes.pop(row)
        self.endRemoveRows()
        return True

    def insert_lane(self, row: int, lane_type: Type[Lane], name: str) -> bool:
        new_lane = None
        if lane_type == DigitalLane:
            new_lane = DigitalLane(
                name=name,
                values=tuple(False for _ in range(self.columnCount())),
                spans=tuple(1 for _ in range(self.columnCount())),
            )
        elif lane_type == AnalogLane:
            new_lane = AnalogLane(
                name=name,
                values=tuple(Expression("...") for _ in range(self.columnCount())),
                spans=tuple(1 for _ in range(self.columnCount())),
                units=self._experiment_config.get_input_units(name),
            )
        elif lane_type == CameraLane:
            new_lane = CameraLane(
                name=name,
                values=(None,) * self.columnCount(),
                spans=(1,) * self.columnCount(),
            )
        if new_lane:
            self.beginInsertRows(QModelIndex(), row, row)
            self._lanes.insert(row, new_lane)
            self.endInsertRows()
            return True
        else:
            return False

    def merge(self, indexes: Iterable[QModelIndex]):
        coordinates = [(index.row(), index.column()) for index in indexes]
        coordinates.sort()
        lanes = groupby(coordinates, key=lambda x: x[0])
        self.beginResetModel()
        for lane, group in lanes:
            l = list(group)
            start = l[0][1]
            stop = l[-1][1] + 1
            self._lanes[lane].merge(start, stop)
        self.endResetModel()

    def break_(self, indexes: Iterable[QModelIndex]):
        coordinates = [(index.row(), index.column()) for index in indexes]
        coordinates.sort()
        lanes = groupby(coordinates, key=lambda x: x[0])
        self.beginResetModel()
        for lane, group in lanes:
            l = list(group)
            start = l[0][1]
            stop = l[-1][1] + 1
            self._lanes[lane].break_(start, stop)
        self.endResetModel()

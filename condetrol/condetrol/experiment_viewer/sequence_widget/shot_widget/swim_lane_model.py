import logging
from itertools import groupby
from typing import Type, Iterable

from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    QSize,
    QTimer,
    QAbstractListModel,
)
from PyQt6.QtGui import QColor, QIcon

from condetrol.utils import UndoStack
from experiment.configuration import ExperimentConfig, ChannelSpecialPurpose
from experiment.session import ExperimentSessionMaker, ExperimentSession
from expression import Expression
from sequence.configuration import (
    DigitalLane,
    AnalogLane,
    Lane,
    CameraLane,
    TakePicture,
    CameraAction,
    Ramp,
    ShotConfiguration,
)
from sequence.runtime import Sequence, State
from settings_model import YAMLSerializable

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class StepNamesModel(QAbstractListModel):
    """Model for the names of the steps

    Note that while it is implemented as a list model with several rows, it is
    displayed horizontally at the top of the swim lane view.
    """

    def __init__(
        self,
        step_names: list[str],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._step_names = step_names

    @property
    def step_names(self):
        return self._step_names

    @step_names.setter
    def step_names(self, step_names: step_names):
        self.beginResetModel()
        self._step_names = step_names
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._step_names)

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._step_names[index.row()]

    def setData(self, index: QModelIndex, value: str, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            self._step_names[index.row()] = value
            return True
        else:
            return False

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginInsertRows(parent, row, row)
        self._step_names.insert(row, "...")
        self.endInsertRows()
        return True

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginRemoveRows(parent, row, row)
        self._step_names.pop(row)
        self.endRemoveRows()
        return True


class StepDurationsModel(QAbstractListModel):
    """Model for the durations of the steps

    Note that while it is implemented as a list model with several rows, it is
    displayed horizontally as the second line of the swim lane view.
    """

    def __init__(self, step_durations: list[Expression], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._step_durations = step_durations

    @property
    def step_durations(self):
        return self._step_durations

    @step_durations.setter
    def step_durations(self, step_durations: list[Expression]):
        self.beginResetModel()
        self._step_durations = step_durations
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._step_durations)

    def data(self, index: QModelIndex, role: int = ...) -> str:
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._step_durations[index.row()].body

    def setData(self, index: QModelIndex, value: str, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            previous = self._step_durations[index.row()].body
            try:
                self._step_durations[index.row()].body = value
            except SyntaxError as error:
                logger.error(error.msg)
                self._step_durations[index.column()].body = previous
                return False
            return True
        else:
            return False

    def insertRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginInsertRows(parent, row, row)
        self._step_durations.insert(row, Expression("..."))
        self.endInsertRows()
        return True

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if parent == ...:
            parent = QModelIndex()
        self.beginRemoveRows(parent, row, row)
        self._step_durations.pop(row)
        self.endRemoveRows()
        return True


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


class SwimLaneModel(QAbstractTableModel):
    """Model for a shot parallel time steps

    Each column corresponds to a time step.
    Row 0 corresponds to the name of the time steps and Row 1 corresponds to the
    duration of the steps. Other rows are device lanes.

    This model is composed of 3 sub-models:
    - A model for the step names
    - A model for the step durations
    - A model for the lanes
    """

    def __init__(
        self,
        sequence: Sequence,
        shot_name: str,
        experiment_config: ExperimentConfig,
        session_maker: ExperimentSessionMaker,
    ):
        super().__init__()
        self._session = session_maker()
        self.experiment_config = experiment_config
        self.shot_name = shot_name
        self._sequence = sequence
        with self._session as session:
            sequence_config = sequence.get_config(session)
        self.shot_config = sequence_config.shot_configurations[self.shot_name]
        self._step_names_model = StepNamesModel(self.shot_config.step_names)
        self._step_durations_model = StepDurationsModel(self.shot_config.step_durations)
        self._lanes_model = LanesModel(self.shot_config.lanes, experiment_config)

        self.undo_stack = UndoStack()
        self.undo_stack.push(self.shot_config.to_yaml())

        # refresh the sequence state to block the editor if the state is not DRAFT
        self._sequence_state: State
        self._update_state()
        self.update_state_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.update_state_timer.timeout.connect(self._update_state)
        self.update_state_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.update_state_timer.start(500)

    def _update_state(self):
        with self._session as session:
            self._sequence_state = self._sequence.get_state(session)

    def get_sequence_state(self, session) -> State:
        return self._sequence.get_state(session)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return 2 + self._lanes_model.rowCount(parent)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        assert (
            self._step_names_model.rowCount()
            == self._step_durations_model.rowCount()
            == self._lanes_model.columnCount()
        )
        return self._step_names_model.rowCount()

    def data(self, index: QModelIndex, role: int = ...):
        if index.row() == 0:
            index = self._step_names_model.index(index.column())
            return self._step_names_model.data(index, role)
        elif index.row() == 1:
            index = self._step_names_model.index(index.column())
            return self._step_durations_model.data(index, role)
        else:
            index = self._lanes_model.index(index.row() - 2, index.column())
            return self._lanes_model.data(index, role)

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        edit = False
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                if index.row() == 0:
                    index = self._step_names_model.index(index.column())
                    edit = self._step_names_model.setData(index, value, role)
                elif index.row() == 1:
                    index = self._step_durations_model.index(index.column())
                    edit = self._step_durations_model.setData(index, value, role)
                else:
                    index = self._lanes_model.index(index.row() - 2, index.column())
                    edit = self._lanes_model.setData(index, value, role)
                if edit:
                    self.save_config(self.shot_config, session)
        return edit

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid():
            flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            if index.row() > 1:
                flags |= Qt.ItemFlag.ItemIsDragEnabled
            if self._sequence_state == State.DRAFT:
                new_index = self._lanes_model.index(index.row() - 2, index.column())
                if self._lanes_model.flags(new_index) & Qt.ItemFlag.ItemIsEditable:
                    flags |= Qt.ItemFlag.ItemIsEditable
                if index.row() > 1:
                    flags |= Qt.ItemFlag.ItemIsDropEnabled
        else:
            flags = Qt.ItemFlag.NoItemFlags
        return flags



    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical:
                if section == 0:
                    return "Name"
                elif section == 1:
                    return "Duration"
                else:
                    return self._lanes_model.headerData(section - 2, orientation, role)
            else:
                return self._step_names_model.headerData(section, orientation, role)

    def span(self, index: QModelIndex) -> QSize:
        if index.row() <= 1:
            return QSize(1, 1)
        else:
            index = self._lanes_model.index(index.row() - 2, index.column())
            return self._lanes_model.span(index)

    def get_lane(self, index: QModelIndex):
        if index.row() >= 1:
            return self.shot_config.lanes[index.row() - 2]

    def insertColumn(self, column: int, parent: QModelIndex = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            self.beginInsertColumns(parent, column, column)
            self._step_names_model.insertRow(column)
            self._step_durations_model.insertRow(column)
            self._lanes_model.insertColumn(column)
            self.endInsertColumns()
            self.save_config(self.shot_config, session)
            self.layoutChanged.emit()
            return True

    def removeColumn(self, column: int, parent: QModelIndex = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            self.beginRemoveColumns(parent, column, column)
            self._step_names_model.removeRow(column)
            self._step_durations_model.removeRow(column)
            self._lanes_model.removeColumn(column)
            self.endRemoveColumns()
            self.save_config(self.shot_config, session)
            self.layoutChanged.emit()
            return True

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        if row < 2:
            return False
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            self.beginRemoveRows(parent, row, row)
            self._lanes_model.removeRow(row - 2)
            self.endRemoveRows()
            self.save_config(self.shot_config, session)
            return True

    def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            self.beginRemoveRows(parent, row, row + count - 1)
            self._lanes_model.removeRows(row - 2, count)
            self.endRemoveRows()
            self.save_config(self.shot_config, session)
            return True

    def insert_lane(self, row: int, lane_type: Type[Lane], name: str):
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return
            self.beginInsertRows(QModelIndex(), row, row)
            self._lanes_model.insert_lane(row - 2, lane_type, name)
            self.endInsertRows()
            self.save_config(self.shot_config, session)

    def save_config(
        self,
        shot_config: ShotConfiguration,
        session: ExperimentSession,
        save_undo: bool = True,
    ):
        self._sequence.set_shot_config(self.shot_name, shot_config, session)

        if save_undo:
            self.undo_stack.push(YAMLSerializable.dump(self.shot_config))

    def merge(self, indexes: Iterable[QModelIndex]):
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return
            indexes = (
                self._lanes_model.index(index.row() - 2, index.column())
                for index in indexes
                if index.row() >= 2
            )
            self._lanes_model.merge(indexes)
            self.save_config(self.shot_config, session)
            self.layoutChanged.emit()

    def break_(self, indexes: Iterable[QModelIndex]):
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return
            indexes = (
                self._lanes_model.index(index.row() - 2, index.column())
                for index in indexes
                if index.row() >= 2
            )
            self._lanes_model.break_(indexes)
            self.save_config(self.shot_config, session)
            self.layoutChanged.emit()

    def undo(self):
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return
            new_yaml = self.undo_stack.undo()
            new_config = ShotConfiguration.from_yaml(new_yaml)
            self.save_config(new_config, session, save_undo=False)
        self.beginResetModel()
        self.shot_config = new_config
        self._step_names_model.step_names = new_config.step_names
        self._step_durations_model.step_durations = new_config.step_durations
        self._lanes_model.lanes = new_config.lanes
        self.endResetModel()
        self.layoutChanged.emit()

    def redo(self):
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return
            new_yaml = self.undo_stack.redo()
            new_config = ShotConfiguration.from_yaml(new_yaml)
            self.save_config(new_config, session, save_undo=False)
        self.beginResetModel()
        self.shot_config = new_config
        self._step_names_model.step_names = new_config.step_names
        self._step_durations_model.step_durations = new_config.step_durations
        self._lanes_model.lanes = new_config.lanes
        self.endResetModel()
        self.layoutChanged.emit()

    def update_experiment_config(self, new_config: ExperimentConfig):
        self.beginResetModel()
        self.experiment_config = new_config
        self._lanes_model.experiment_config = new_config
        self.endResetModel()

    # noinspection PyTypeChecker
    # def supportedDropActions(self) -> Qt.DropAction:
    #     return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction
    #
    # def supportedDragActions(self) -> Qt.DropAction:
    #     with self._session as session:
    #         if self.get_sequence_state(session) == State.DRAFT:
    #             return Qt.DropAction.MoveAction
    #         else:
    #             return Qt.DropAction.CopyAction
    #
    # def mimeTypes(self) -> list[str]:
    #     return ["application/x-shot_lanes"]
    #
    # def mimeData(self, indexes: Iterable[QModelIndex]) -> QMimeData:
    #     rows = set(index.row() for index in indexes)
    #     data = [self.shot_config.lanes[row - 2] for row in rows]
    #     serialized = YAMLSerializable.dump(data).encode("utf-8")
    #     mime_data = QMimeData()
    #     mime_data.setData("application/x-shot_lanes", QByteArray(serialized))
    #     logger.debug(data)
    #     return mime_data
    #
    # def dropMimeData(
    #     self,
    #     data: QMimeData,
    #     action: Qt.DropAction,
    #     row: int,
    #     column: int,
    #     parent: QModelIndex,
    # ) -> bool:
    #     yaml_string = data.data("application/x-shot_lanes").data().decode("utf-8")
    #     lanes: list[Lane] = YAMLSerializable.load(yaml_string)
    #     return False
    #
    #     correct_length = all(
    #         len(lane) == len(self.shot_config.step_names) for lane in lanes
    #     )
    #     if correct_length:
    #         self.beginInsertRows(parent, row, row + len(lanes) - 1)
    #         for lane in lanes:
    #             logger.debug(row)
    #             self.shot_config.lanes.insert(row - 2, lane)
    #         self.endInsertRows()
    #         self.save_config()
    #         return True
    #     else:
    #         return False

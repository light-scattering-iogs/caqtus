import logging
from typing import Type, Iterable

from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    QSize,
    QTimer,
    QAbstractItemModel,
)

from condetrol.utils import UndoStack
from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.configuration import (
    Lane,
    ShotConfiguration,
    LaneReference,
)
from sequence.runtime import Sequence, State
from settings_model import YAMLSerializable
from .lane_groups_model import LaneGroupModel
from .lanes_model import LanesModel
from .step_durations_model import StepDurationsModel
from .step_names_model import StepNamesModel

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class SwimLaneModel(QAbstractItemModel):

    """
    First column corresponds the name of the lanes/lane groups.
    Other columns correspond to the steps of the sequence.

    step_names:
        - row == 0
        - column >= 1
        - internalPointer == None
    step_durations:
        - row == 1
        - column >= 1
        - internalPointer == None
    lane_groups:
        - row >= 2
        - column == 0
        - internalPointer == lane_group
    lanes:
        - row >= 2
        - column >= 1
        - internalPointer == lane_group
    """

    def __init__(
        self,
        sequence: Sequence,
        shot_name: str,
        experiment_config: ExperimentConfig,
        session_maker: ExperimentSessionMaker,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        with session_maker() as session:
            sequence_config = sequence.get_config(session)

        shot_config = sequence_config.shot_configurations[shot_name]

        self._step_names_model = StepNamesModel(shot_config.step_names)
        self._step_durations_model = StepDurationsModel(shot_config.step_durations)
        self._lane_groups_model = LaneGroupModel(shot_config.lane_groups)
        self._lanes_model = LanesModel(shot_config.lanes, experiment_config)

        self._lanes_mapping = self._get_lane_names_to_index_mapping(shot_config.lanes)

    @staticmethod
    def _get_lane_names_to_index_mapping(lanes: list[Lane]) -> dict[str, int]:
        return {lane.name: i for i, lane in enumerate(lanes)}

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 1 + self._lanes_model.columnCount()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        mapped_parent = self.map_to_lane_groups_model(parent)
        row_count = self._lane_groups_model.rowCount(mapped_parent)
        return row_count

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        mapped_parent = self.map_to_lane_groups_model(parent)
        mapped_child = self._lane_groups_model.index(row, 0, mapped_parent)
        return self.createIndex(
            mapped_child.row(), column, mapped_child.internalPointer()
        )

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()
        mapped_child = self.map_to_lane_groups_model(child)
        mapped_parent = mapped_child.parent()
        return self.map_from_lane_groups_model(child.column(), mapped_parent)

    def map_to_child_index(self, index: QModelIndex) -> QModelIndex:
        if index.column() == 0:
            return self.map_to_lane_groups_model(index)
        else:
            return self.map_to_lanes_model(index)

    def map_to_lane_groups_model(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return self._lane_groups_model.index(index.row() - 2, 0, QModelIndex())
        else:
            return self._lane_groups_model.createIndex(
                index.row(),
                0,
                index.internalPointer(),
            )

    def map_from_lane_groups_model(
        self, column: int, index: QModelIndex
    ) -> QModelIndex:
        return self.createIndex(index.row(), column, index.internalPointer())

    def map_to_lanes_model(self, index: QModelIndex) -> QModelIndex:
        item = index.internalPointer()
        if isinstance(item, LaneReference):
            row = self._lanes_mapping[item.lane_name]
            return self._lanes_model.index(row, index.column() - 1, QModelIndex())
        else:
            return QModelIndex()

    def data(self, index: QModelIndex, role: int = ...):
        if not index.isValid():
            return None
        mapped_index = self.map_to_child_index(index)
        return mapped_index.data(role)


class _SwimLaneModel(QAbstractTableModel):
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

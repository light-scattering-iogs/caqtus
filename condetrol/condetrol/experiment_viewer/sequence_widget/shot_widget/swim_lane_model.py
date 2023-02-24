import logging
from functools import partial
from typing import Type, Iterable, Optional

from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    Qt,
    QSize,
    QTimer,
    QAbstractItemModel,
)
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from condetrol.utils import UndoStack
from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.configuration import (
    Lane,
    ShotConfiguration,
    LaneReference,
    DigitalLane, AnalogLane, CameraLane,
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

    """

    def __init__(
        self,
        sequence: Sequence,
        shot_name: str,
        experiment_config: ExperimentConfig,
        session_maker: ExperimentSessionMaker,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._session = session_maker()
        self._sequence = sequence
        self.shot_name = shot_name
        self._experiment_config = experiment_config

        with self._session:
            sequence_config = self._sequence.get_config(self._session)

        self.shot_config = sequence_config.shot_configurations[self.shot_name]

        self._step_names_model = StepNamesModel(self.shot_config.step_names)
        self._step_durations_model = StepDurationsModel(self.shot_config.step_durations)
        self._lane_groups_model = LaneGroupModel(self.shot_config.lane_groups)
        self._lanes_model = LanesModel(self.shot_config.lanes, self._experiment_config)

        # refresh the sequence state to block the editor if the state is not DRAFT
        self._sequence_state: State
        self._update_state()
        self.update_state_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.update_state_timer.timeout.connect(self._update_state)
        self.update_state_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.update_state_timer.start(500)

    @property
    def sequence(self):
        return self._sequence

    def _update_state(self):
        with self._session as session:
            self._sequence_state = self._sequence.get_state(session)

    def save_config(
        self,
        shot_config: ShotConfiguration,
        session: ExperimentSession,
        save_undo: bool = True,
    ):
        self._sequence.set_shot_config(self.shot_name, shot_config, session)

        # if save_undo:
        #     self.undo_stack.push(YAMLSerializable.dump(self.shot_config))

    def get_sequence_state(self, session) -> State:
        return self._sequence.get_state(session)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        assert (
            count := self._step_names_model.rowCount()
        ) == self._step_durations_model.rowCount()
        return 1 + count

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return 2 + self._lane_groups_model.rowCount(QModelIndex())
        else:
            internal_pointer = parent.internalPointer()
            if internal_pointer is None:
                return 0
            else:
                mapped_parent = self._lane_groups_model.createIndex(
                    parent.row(), 0, parent.internalPointer()
                )
                return self._lane_groups_model.rowCount(mapped_parent)

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            if row < 2:
                internal_pointer = None
            else:
                internal_pointer = self._lane_groups_model.index(
                    row - 2, 0, QModelIndex()
                ).internalPointer()
        else:
            mapped_parent = self._lane_groups_model.createIndex(
                parent.row(),
                0,
                parent.internalPointer(),
            )
            mapped_child = self._lane_groups_model.index(row, 0, mapped_parent)
            internal_pointer = mapped_child.internalPointer()

        return self.createIndex(
            row,
            column,
            internal_pointer,
        )

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()
        internal_pointer = child.internalPointer()
        if internal_pointer is None:
            return QModelIndex()
        if internal_pointer.parent.is_root:
            return QModelIndex()
        else:
            mapped_child = self._lane_groups_model.createIndex(
                child.row(), 0, internal_pointer
            )
            mapped_parent = mapped_child.parent()
            return self.createIndex(
                mapped_parent.row(), child.column(), mapped_parent.internalPointer()
            )

    def map_to_child_index(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        internal_pointer = index.internalPointer()
        if internal_pointer is None:
            if index.column() == 0:
                return QModelIndex()
            if index.row() == 0:
                return self._step_names_model.index(
                    index.column() - 1, 0, QModelIndex()
                )
            elif index.row() == 1:
                return self._step_durations_model.index(
                    index.column() - 1, 0, QModelIndex()
                )
            else:
                raise ValueError("Cannot map to child index")
        else:
            if index.column() == 0:
                if index.parent().isValid():
                    row = index.row()
                else:
                    row = index.row() - 2
                return self._lane_groups_model.createIndex(row, 0, internal_pointer)
            else:
                if isinstance(internal_pointer, LaneReference):
                    row = self._lanes_model.map_name_to_row(internal_pointer.lane_name)
                    return self._lanes_model.index(
                        row, index.column() - 1, QModelIndex()
                    )
        return QModelIndex()

    def data(self, index: QModelIndex, role: int = ...):
        if not index.isValid():
            return None
        mapped_index = self.map_to_child_index(index)
        return mapped_index.data(role)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if orientation == Qt.Orientation.Horizontal:
            if section == 0:
                if role == Qt.ItemDataRole.DisplayRole:
                    return "Lanes\\Steps"
            else:
                return self._step_names_model.headerData(
                    section - 1, Qt.Orientation.Vertical, role
                )
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemDataRole.NoItemFlags
        mapped_index = self.map_to_child_index(index)
        flags = mapped_index.flags()
        if self._sequence_state != State.DRAFT:
            flags &= ~Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        edit = False
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                mapped_index = self.map_to_child_index(index)
                edit = mapped_index.model().setData(mapped_index, value, role)
                if edit:
                    self.save_config(self.shot_config, session)
                    self.dataChanged.emit(index, index, [role])
        return edit

    def insertColumn(self, column: int, parent: QModelIndex = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            if column == 0:
                return False
            else:
                column -= 1
            self.beginInsertColumns(parent, column, column)
            self._step_names_model.insertRow(column)
            self._step_durations_model.insertRow(column)
            self._lanes_model.insertColumn(column)
            self.endInsertColumns()
            logger.debug(self.shot_config.step_names)
            self.save_config(self.shot_config, session)
            return True

    def removeColumn(self, column: int, parent: QModelIndex = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            if column == 0:
                return False
            else:
                column -= 1
            self.beginRemoveColumns(parent, column, column)
            self._step_names_model.removeRow(column)
            self._step_durations_model.removeRow(column)
            self._lanes_model.removeColumn(column)
            self.endRemoveColumns()
            self.save_config(self.shot_config, session)
            return True

    def get_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        result = []
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return result
        if (insert := self.get_insert_lane_action(index)) is not None:
            result.append(insert)
        if (remove := self.get_remove_lane_or_group_action(index)) is not None:
            result.append(remove)
        return result

    def get_insert_lane_action(self, index: QModelIndex) -> Optional[QMenu]:
        if not index.isValid():
            return None
        if index.column() == 0:
            insert_menu = QMenu("Insert lane")

            insert_digital = insert_menu.addMenu("digital")
            insert_analog = insert_menu.addMenu("analog")
            insert_camera = insert_menu.addMenu("camera")

            if index.row() < 2:
                self.add_lane_create_action(insert_digital, DigitalLane, QModelIndex())
                self.add_lane_create_action(insert_analog, AnalogLane, QModelIndex())
                self.add_lane_create_action(insert_camera, CameraLane, QModelIndex())

                return insert_menu

    def add_lane_create_action(
        self, menu: QMenu, lane_type: Type[Lane], insert_index: QModelIndex
    ):
        already_in_use_channels = set(self.shot_config.get_lane_names())

        possible_channels = self._experiment_config.get_available_lane_names(
            lane_type
        )

        available_channels = sorted(
            possible_channels - already_in_use_channels
        )
        for channel in available_channels:
            action = menu.addAction(channel)
            action.triggered.connect(
                partial(
                    self.insert_lane,
                    insert_index,
                    lane_type,
                    channel,
                )
            )

    def insert_lane(self, index: QModelIndex, lane_type: Type[Lane], name: str):
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return

            if not index.isValid():  # insert as first element of root
                self.beginInsertRows(QModelIndex(), 2, 2)
                self._lanes_model.insert_lane(
                    0, lane_type, name, self._step_names_model.rowCount()
                )
                self._lane_groups_model.insert_lane(QModelIndex(), 0, name)
                self.endInsertRows()
                self.save_config(self.shot_config, session)
            else:
                raise NotImplementedError()

    def get_remove_lane_or_group_action(self, index: QModelIndex) -> Optional[QAction]:
        mapped_index = self.map_to_child_index(index)
        if mapped_index.model() is self._lane_groups_model:
            remove = QAction("Remove")
            remove.triggered.connect(
                lambda: self.removeRow(index.row(), index.parent())
            )
            return remove

    def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            child = self.index(row, 0, parent)
            mapped_child = self.map_to_child_index(child)
            if not mapped_child.model() is self._lane_groups_model:
                return False
            if not self._lane_groups_model.is_lane(mapped_child):
                raise NotImplementedError()
            lane_name = self._lane_groups_model.data(
                mapped_child, Qt.ItemDataRole.DisplayRole
            )
            self.beginRemoveRows(parent, row, row)
            self._lane_groups_model.removeRow(mapped_child.row(), mapped_child.parent())
            self._lanes_model.removeRow(self._lanes_model.map_name_to_row(lane_name))
            self.endRemoveRows()
            self.save_config(self.shot_config, session)
            return True


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
            self._step_names_model.rowCount() == self._step_durations_model.rowCount()
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

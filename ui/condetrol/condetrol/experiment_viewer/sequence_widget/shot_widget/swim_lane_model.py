import logging
from functools import partial
from types import NotImplementedType
from typing import Type, Iterable, Optional, Any

from PyQt6.QtCore import (
    QModelIndex,
    Qt,
    QSize,
    QAbstractItemModel,
)
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QWidget

from analog_lane.configuration import AnalogLane
from atom_detector_lane.configuration import AtomDetectorLane
from camera_lane.configuration import CameraLane
from concurrent_updater.sequence_state_watcher import SequenceStateWatcher
from digital_lane.configuration import DigitalLane
from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker, ExperimentSession
from lane.configuration import Lane
from sequence.configuration import ShotConfiguration, LaneReference
from sequence.runtime import Sequence, State
from tweezer_arranger_lane.configuration import TweezerArrangerLane
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
        sequence_state_watcher: SequenceStateWatcher,
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

        self._state_updater = sequence_state_watcher

    @property
    def sequence_state(self) -> State:
        return self._state_updater.sequence_state

    @property
    def sequence(self):
        return self._sequence

    def save(self) -> bool:
        """Save the shot config edited by the model to persistent storage.

        Returns:
            True if the sequence is editable and the shot config was saved. False otherwise.
        """
        with self._session.activate():
            if self.get_sequence_state(self._session).is_editable():
                self._save_config(self.shot_config, self._session)
                return True
            else:
                return False

    def _save_config(
        self,
        shot_config: ShotConfiguration,
        session: ExperimentSession,
        save_undo: bool = True,
    ):
        self._sequence.set_shot_config(self.shot_name, shot_config, session)

        # if save_undo:
        #     self.undo_stack.push(YAMLSerializable.dump(self.shot_config))

    def set_shot_config(self, shot_config: ShotConfiguration):
        self.beginResetModel()

        self.shot_config = shot_config
        self._step_names_model = StepNamesModel(self.shot_config.step_names)
        self._step_durations_model = StepDurationsModel(self.shot_config.step_durations)
        self._lane_groups_model = LaneGroupModel(self.shot_config.lane_groups)
        self._lanes_model = LanesModel(self.shot_config.lanes, self._experiment_config)

        with self._session as session:
            self._save_config(shot_config, session)
        self.endResetModel()

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

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        mapped_index = self.map_to_child_index(index)
        if mapped_index.isValid():
            return mapped_index.data(role)
        if index.row() == 0 and index.column() == 0:
            if role == Qt.ItemDataRole.SizeHintRole:
                return QSize(0, 25)

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
        if self.sequence_state != State.DRAFT:
            flags &= ~Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(
        self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        edit = False
        with self._session as session:
            if self.get_sequence_state(session) == State.DRAFT:
                mapped_index = self.map_to_child_index(index)
                if mapped_index.isValid():
                    edit = mapped_index.model().setData(mapped_index, value, role)
                else:
                    edit = super().setData(index, value, role)
                if edit:
                    self._save_config(self.shot_config, session)
                    self.dataChanged.emit(index, index, [role])
        return edit

    def insertColumn(self, column: int, parent: QModelIndex = QModelIndex()) -> bool:
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
            self._save_config(self.shot_config, session)
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
            self._save_config(self.shot_config, session)
            return True

    def get_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        result: list[QAction | QMenu] = []
        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return result
        if (insert := self.get_insert_lane_action(index)) is not None:
            result.append(insert)
        if (remove := self.get_remove_lane_or_group_action(index)) is not None:
            result.append(remove)

        mapped_index = self.map_to_child_index(index)
        if mapped_index.model() is self._lanes_model:
            result.extend(self._lanes_model.get_cell_context_actions(mapped_index))
        return result

    def get_insert_lane_action(self, index: QModelIndex) -> Optional[QMenu]:
        if not index.isValid():
            return None
        if index.column() == 0:
            insert_menu = QMenu("Insert lane")

            insert_digital = insert_menu.addMenu("digital")
            insert_analog = insert_menu.addMenu("analog")
            insert_camera = insert_menu.addMenu("camera")
            insert_arranger = insert_menu.addMenu("arranger")
            insert_detector = insert_menu.addMenu("detector")

            if index.row() < 2:
                self.add_lane_create_action(insert_digital, DigitalLane, QModelIndex())
                self.add_lane_create_action(insert_analog, AnalogLane, QModelIndex())
                self.add_lane_create_action(insert_camera, CameraLane, QModelIndex())
                self.add_lane_create_action(
                    insert_arranger, TweezerArrangerLane, QModelIndex()
                )
                self.add_lane_create_action(
                    insert_detector, AtomDetectorLane, QModelIndex()
                )

                return insert_menu

    def add_lane_create_action(
        self, menu: QMenu, lane_type: Type[Lane], insert_index: QModelIndex
    ):
        already_in_use_channels = set(self.shot_config.get_lane_names())

        possible_channels = self._experiment_config.get_available_lane_names(lane_type)

        available_channels = sorted(possible_channels - already_in_use_channels)
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
                self._save_config(self.shot_config, session)
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

    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
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
            self._save_config(self.shot_config, session)
            return True

    def span(self, index: QModelIndex) -> QSize:
        mapped_index = self.map_to_child_index(index)
        if mapped_index.model() is self._lanes_model:
            return self._lanes_model.span(mapped_index)
        else:
            return QSize(1, 1)

    def is_lane_cell(self, index: QModelIndex) -> bool:
        mapped_index = self.map_to_child_index(index)
        return mapped_index.model() is self._lanes_model

    def is_lane_group_cell(self, index: QModelIndex) -> bool:
        mapped_index = self.map_to_child_index(index)
        return mapped_index.model() is self._lane_groups_model

    def is_step_cell(self, index: QModelIndex) -> bool:
        mapped_index = self.map_to_child_index(index)
        return (
            mapped_index.model() is self._step_names_model
            or mapped_index.model() is self._step_durations_model
        )

    def merge(self, indexes: Iterable[QModelIndex]) -> bool:
        """Attempt to merge the cells of lanes"""

        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            mapped_indexes = []
            for index in indexes:
                mapped_index = self.map_to_child_index(index)
                if mapped_index.model() is self._lanes_model:
                    mapped_indexes.append(mapped_index)
                else:
                    return False
            result = self._lanes_model.merge(mapped_indexes)
            self._save_config(self.shot_config, session)
            return result

    def break_up(self, indexes: Iterable[QModelIndex]) -> bool:
        """Attempt to break up the cells of lanes"""

        with self._session as session:
            if self.get_sequence_state(session) != State.DRAFT:
                return False
            mapped_indexes = []
            for index in indexes:
                mapped_index = self.map_to_child_index(index)
                if mapped_index.model() is self._lanes_model:
                    mapped_indexes.append(mapped_index)
                else:
                    return False
            result = self._lanes_model.break_up(mapped_indexes)
            self._save_config(self.shot_config, session)
            return result

    def create_editor(
        self, parent: QWidget, index: QModelIndex
    ) -> QWidget | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        mapped_index = self.map_to_child_index(index)
        if mapped_index.model() is self._lanes_model:
            return self._lanes_model.create_editor(parent, mapped_index)
        return NotImplemented

    def set_editor_data(
        self, editor: QWidget, index: QModelIndex
    ) -> None | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        mapped_index = self.map_to_child_index(index)
        if mapped_index.model() is self._lanes_model:
            return self._lanes_model.set_editor_data(editor, mapped_index)
        return NotImplemented

    def get_editor_data(
        self, editor: QWidget, index: QModelIndex
    ) -> Any | NotImplementedType:
        if not index.isValid():
            return NotImplemented
        mapped_index = self.map_to_child_index(index)
        if mapped_index.model() is self._lanes_model:
            return self._lanes_model.get_editor_data(editor, mapped_index)
        return NotImplemented

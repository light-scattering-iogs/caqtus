import functools
from typing import Optional

from PySide6.QtCore import (
    QAbstractTableModel,
    QObject,
    QModelIndex,
    Qt,
    QSize,
    QPersistentModelIndex,
)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from caqtus.gui.qtutil import qabc as qabc
from caqtus.types.timelane import TimeLanes, TimeLane
from ._time_step_model import (
    TimeStepNameModel,
    TimeStepDurationModel,
)
from .extension import CondetrolLaneExtensionProtocol
from .model import TimeLaneModel

_DEFAULT_MODEL_INDEX = QModelIndex()


class TimeLanesModel(QAbstractTableModel, metaclass=qabc.QABCMeta):
    # Ignore some lint rules for this file as PySide6 models have a lot of camelCase
    # methods.
    # ruff: noqa: N802
    def __init__(
        self,
        extension: "CondetrolLaneExtensionProtocol",
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._step_names_model = TimeStepNameModel(self)
        self._step_durations_model = TimeStepDurationModel(self)
        self._lane_models: list[TimeLaneModel] = []
        self._extension = extension

        self._step_names_model.dataChanged.connect(self.on_step_names_data_changed)
        self._step_durations_model.dataChanged.connect(
            self.on_step_durations_data_changed
        )
        self._read_only = False

    def set_read_only(self, read_only: bool) -> None:
        self._read_only = read_only

    def is_read_only(self) -> bool:
        return self._read_only

    def on_step_names_data_changed(
        self,
        top_left: QModelIndex,
        bottom_right: QModelIndex,
        roles: list[Qt.ItemDataRole],
    ):
        self.dataChanged.emit(
            self.index(0, top_left.row()), self.index(0, bottom_right.row())
        )

    def on_step_durations_data_changed(
        self,
        top_left: QModelIndex,
        bottom_right: QModelIndex,
        roles: list[Qt.ItemDataRole],
    ):
        self.dataChanged.emit(
            self.index(1, top_left.row()), self.index(1, bottom_right.row())
        )

    def set_timelanes(self, timelanes: TimeLanes):
        # Don't check if read only, because we need to update the content of the editor
        # even if it is readonly when swapping sequences.
        new_models = []
        for name, lane in timelanes.lanes.items():
            lane_model = self.create_lane_model(name, lane)
            new_models.append(lane_model)

        self.beginResetModel()
        self._step_names_model.set_names(timelanes.step_names)
        self._step_durations_model.set_durations(timelanes.step_durations)
        self._lane_models.clear()
        self._lane_models.extend(new_models)
        self.endResetModel()

    def create_lane_model(self, name: str, lane: TimeLane) -> TimeLaneModel:
        lane_model = self._extension.get_lane_model(lane, name)
        lane_model.setParent(self)
        lane_model.set_lane(lane)
        lane_model.dataChanged.connect(
            # For some reason, functools.partial does not work here, but lambda does.
            # functools.partial(
            #     self.on_lane_model_data_changed, lane_model=lane_model
            # )
            lambda top_left, bottom_right: self.on_lane_model_data_changed(
                top_left, bottom_right, lane_model
            )
        )
        lane_model.headerDataChanged.connect(
            functools.partial(self.on_lane_header_data_changed, lane_model=lane_model)
        )
        return lane_model

    def on_lane_model_data_changed(
        self,
        top_left: QModelIndex,
        bottom_right: QModelIndex,
        lane_model: TimeLaneModel,
    ):
        lane_index = self._lane_models.index(lane_model)
        self.dataChanged.emit(
            self.index(lane_index + 2, top_left.row()),
            self.index(lane_index + 2, bottom_right.row()),
        )

    def on_lane_header_data_changed(
        self,
        orientation: Qt.Orientation,
        first: int,
        last: int,
        lane_model: TimeLaneModel,
    ):
        lane_index = self._lane_models.index(lane_model)
        if orientation == Qt.Orientation.Horizontal:
            self.headerDataChanged.emit(
                Qt.Orientation.Vertical,
                lane_index + 2,
                lane_index + 2,
            )

    def insert_time_lane(
        self, name: str, timelane: TimeLane, index: Optional[int] = None
    ):
        if self._read_only:
            return
        if index is None:
            index = len(self._lane_models)
        if not (0 <= index <= len(self._lane_models)):
            raise IndexError(f"Index {index} is out of range")
        if len(timelane) != self.columnCount():
            raise ValueError(
                f"Length of time lane ({len(timelane)}) does not match "
                f"number of columns ({self.columnCount()})"
            )
        already_used_names = {
            model.headerData(0, Qt.Orientation.Horizontal)
            for model in self._lane_models
        }
        if name in already_used_names:
            raise ValueError(f"Name {name} is already used")
        lane_model = self.create_lane_model(name, timelane)
        self.beginInsertRows(QModelIndex(), index, index)
        self._lane_models.insert(index, lane_model)
        self.endInsertRows()

    def get_lane(self, index: int) -> TimeLane:
        return self._lane_models[index].get_lane()

    def get_lane_name(self, index: int) -> str:
        return get_lane_model_name(self._lane_models[index])

    def get_timelanes(self) -> TimeLanes:
        """Return a copy of the lanes currently in the model."""

        return TimeLanes(
            step_names=self._step_names_model.get_names(),
            step_durations=self._step_durations_model.get_duration(),
            lanes={
                get_lane_model_name(model): model.get_lane()
                for model in self._lane_models
            },
        )

    def columnCount(self, parent=_DEFAULT_MODEL_INDEX) -> int:
        count = self._step_names_model.rowCount()
        assert count == self._step_durations_model.rowCount()
        assert all(model.rowCount() == count for model in self._lane_models), [
            model.rowCount() for model in self._lane_models
        ]
        return count

    def rowCount(self, parent=_DEFAULT_MODEL_INDEX) -> int:
        return len(self._lane_models) + 2

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        return self._map_to_source(index).data(role)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if self._read_only:
            return False
        if not index.isValid():
            return False
        mapped_index = self._map_to_source(index)
        return mapped_index.model().setData(mapped_index, value, role)

    def flags(self, index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        mapped_index = self._map_to_source(index)
        flags = mapped_index.model().flags(mapped_index)
        if self._read_only:
            flags &= ~Qt.ItemFlag.ItemIsEditable
            flags &= ~Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role=Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return f"Step {section}"
        elif orientation == Qt.Orientation.Vertical:
            if section == 0:
                return self._step_names_model.headerData(
                    0, Qt.Orientation.Horizontal, role
                )
            elif section == 1:
                return self._step_durations_model.headerData(
                    0, Qt.Orientation.Horizontal, role
                )
            else:
                return self._lane_models[section - 2].headerData(
                    0, Qt.Orientation.Horizontal, role
                )

    def insertColumn(self, column, parent=_DEFAULT_MODEL_INDEX) -> bool:
        if self._read_only:
            return False
        if not (0 <= column <= self.columnCount()):
            return False
        self.beginInsertColumns(parent, column, column)
        self._step_names_model.insertRow(column)
        self._step_durations_model.insertRow(column)
        for lane_model in self._lane_models:
            lane_model.insertRow(column)
        self.endInsertColumns()
        self.modelReset.emit()

        return True

    def removeColumn(self, column, parent=_DEFAULT_MODEL_INDEX) -> bool:
        if self._read_only:
            return False
        if not (0 <= column < self.columnCount()):
            return False
        self.beginRemoveColumns(parent, column, column)
        self._step_names_model.removeRow(column)
        self._step_durations_model.removeRow(column)
        for lane_model in self._lane_models:
            lane_model.removeRow(column)
        self.endRemoveColumns()
        self.modelReset.emit()
        return True

    def removeRow(self, row, parent=_DEFAULT_MODEL_INDEX) -> bool:
        if self._read_only:
            return False
        if not (2 <= row < self.rowCount()):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._lane_models[row - 2]
        self.endRemoveRows()
        return True

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        if not index.isValid():
            return []
        if self._read_only:
            return []
        if index.row() >= 2:
            return self._lane_models[index.row() - 2].get_cell_context_actions(
                self._map_to_source(index)
            )
        else:
            return []

    def get_lane_header_context_actions(self, lane_index: int) -> list[QAction | QMenu]:
        if not 0 <= lane_index < len(self._lane_models):
            return []
        if self._read_only:
            return []
        return self._lane_models[lane_index].get_header_context_actions()

    def span(self, index):
        if not index.isValid():
            return QSize(1, 1)
        if index.row() >= 2:
            mapped_index = self._map_to_source(index)
            span = self._lane_models[index.row() - 2].span(mapped_index)
            return QSize(span.height(), span.width())
        return QSize(1, 1)

    def expand_step(self, step: int, lane_index: int, start: int, stop: int):
        if self._read_only:
            return
        lane_model = self._lane_models[lane_index]
        lane_model.expand_step(step, start, stop)

    def _map_to_source(self, index: QModelIndex | QPersistentModelIndex) -> QModelIndex:
        assert index.isValid()
        assert self.hasIndex(index.row(), index.column())
        if index.row() == 0:
            return self._step_names_model.index(index.column(), 0)
        elif index.row() == 1:
            return self._step_durations_model.index(index.column(), 0)
        else:
            return self._lane_models[index.row() - 2].index(index.column(), 0)

    def simplify(self) -> None:
        self.beginResetModel()
        for lane_model in self._lane_models:
            lane_model.simplify()
        self.endResetModel()


def get_lane_model_name(model: TimeLaneModel) -> str:
    lane_name = model.headerData(
        0, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
    )
    if not isinstance(lane_name, str):
        raise TypeError(f"Expected str, got {type(lane_name)}")
    return lane_name

import abc
import copy
import functools
from collections.abc import Callable
from typing import Optional, Any

from PyQt6.QtCore import (
    QAbstractTableModel,
    QObject,
    QModelIndex,
    QAbstractListModel,
    Qt,
    QSize,
)
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from core.session.shot import TimeLane
from core.session.shot.timelane import TimeLanes
from core.types.expression import Expression
from qabc import qabc


class TimeStepNameModel(QAbstractListModel):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._names: list[str] = []

    def set_names(self, names: list[str]):
        self.beginResetModel()
        self._names = copy.deepcopy(names)
        self.endResetModel()

    def get_names(self) -> list[str]:
        return copy.deepcopy(self._names)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._names)

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._names[index.row()]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            if not isinstance(value, str):
                raise TypeError(f"Expected str, got {type(value)}")
            self._names[index.row()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def insertRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row <= self.rowCount()):
            return False
        self.beginInsertRows(parent, row, row)
        self._names.insert(row, f"Step {row}")
        self.endInsertRows()
        return True

    def removeRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row < self.rowCount()):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._names[row]
        self.endRemoveRows()
        return True


class TimeStepDurationModel(QAbstractListModel):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._durations: list[Expression] = []

    def set_durations(self, durations: list[Expression]):
        self.beginResetModel()
        self._durations = copy.deepcopy(durations)
        self.endResetModel()

    def get_duration(self) -> list[Expression]:
        return copy.deepcopy(self._durations)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._durations)

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self._durations[index.row()].body
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            if not isinstance(value, str):
                raise TypeError(f"Expected str, got {type(value)}")
            self._durations[index.row()].body = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )

    def insertRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row <= self.rowCount()):
            return False
        self.beginInsertRows(parent, row, row)
        self._durations.insert(row, Expression("..."))
        self.endInsertRows()
        return True

    def removeRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row < self.rowCount()):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._durations[row]
        self.endRemoveRows()
        return True


class TimeLaneModel[L: TimeLane, O](QAbstractListModel, qabc.QABC):
    @abc.abstractmethod
    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._name = name

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._name
            elif orientation == Qt.Orientation.Vertical:
                return section

    @abc.abstractmethod
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ):
        raise NotImplementedError

    @abc.abstractmethod
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        raise NotImplementedError

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsSelectable
        )

    @abc.abstractmethod
    def set_lane(self, lane: L) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_lane(self) -> L:
        raise NotImplementedError

    @abc.abstractmethod
    def set_display_options(self, options: O) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def insertRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def removeRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        raise NotImplementedError

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        return []

    @abc.abstractmethod
    def span(self, index) -> QSize:
        raise NotImplementedError

    def merge_cells(self, start: int, stop: int) -> None:
        raise NotImplementedError


type LaneModelFactory[L: TimeLane] = Callable[[L], type[TimeLaneModel[L, Any]]]


class TimeLanesModel(QAbstractTableModel, qabc.QABC):
    def __init__(
        self, lane_model_factory: LaneModelFactory, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._step_names_model = TimeStepNameModel(self)
        self._step_durations_model = TimeStepDurationModel(self)
        self._lane_models: list[TimeLaneModel] = []
        self._lane_model_factory = lane_model_factory

    def set_timelanes(self, timelanes: TimeLanes):
        new_models = []
        for index, (name, lane) in enumerate(timelanes.lanes.items()):
            lane_model = self._lane_model_factory(lane)(name, self)
            lane_model.set_lane(lane)
            lane_model.dataChanged.connect(
                functools.partial(self.on_lane_model_data_changed, lane_index=index)
            )
            new_models.append(lane_model)

        self.beginResetModel()
        self._step_names_model.set_names(timelanes.step_names)
        self._step_durations_model.set_durations(timelanes.step_durations)
        self._lane_models.clear()
        self._lane_models.extend(new_models)
        self.endResetModel()

    def on_lane_model_data_changed(
        self, top_left: QModelIndex, bottom_right: QModelIndex, lane_index: int
    ):
        self.dataChanged.emit(
            self.index(lane_index + 2, top_left.row()),
            self.index(lane_index + 2, bottom_right.row()),
        )

    def insert_timelane(self, index: int, name: str, timelane: TimeLane):
        if not (0 <= index <= len(self._lane_models)):
            raise IndexError(f"Index {index} is out of range")
        if len(timelane) != self.columnCount():
            raise ValueError(
                f"Length of timelane ({len(timelane)}) does not match "
                f"number of columns ({self.columnCount()})"
            )
        already_used_names = {
            model.headerData(0, Qt.Orientation.Horizontal)
            for model in self._lane_models
        }
        if name in already_used_names:
            raise ValueError(f"Name {name} is already used")
        lane_model = self._lane_model_factory(timelane)(name, self)
        lane_model.set_lane(timelane)
        self.beginInsertRows(QModelIndex(), index, index)
        self._lane_models.insert(index, lane_model)
        self.endInsertRows()

    def get_lane(self, index: int) -> TimeLane:
        return self._lane_models[index].get_lane()

    def get_timelanes(self) -> TimeLanes:
        return TimeLanes(
            step_names=self._step_names_model.get_names(),
            step_durations=self._step_durations_model.get_duration(),
            lanes={
                model.headerData(0, Qt.Orientation.Horizontal): model.get_lane()
                for model in self._lane_models
            },
        )

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        count = self._step_names_model.rowCount()
        assert count == self._step_durations_model.rowCount()
        assert all(model.rowCount() == count for model in self._lane_models)
        return count

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._lane_models) + 2

    def data(self, index, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        return self._map_to_source(index).data(role)

    def setData(self, index, value, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        mapped_index = self._map_to_source(index)
        if mapped_index.model().setData(mapped_index, value, role):
            self.dataChanged.emit(index, index)
            return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        mapped_index = self._map_to_source(index)
        return mapped_index.model().flags(mapped_index)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return f"Step {section}"
        elif orientation == Qt.Orientation.Vertical:
            if section == 0:
                if role == Qt.ItemDataRole.DisplayRole:
                    return "Step name"
            elif section == 1:
                if role == Qt.ItemDataRole.DisplayRole:
                    return "Step duration"
            else:
                return self._lane_models[section - 2].headerData(
                    0, Qt.Orientation.Horizontal, role
                )

    def insertColumn(self, column, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= column <= self.columnCount()):
            return False
        self.beginInsertColumns(parent, column, column)
        self._step_names_model.insertRow(column)
        self._step_durations_model.insertRow(column)
        for lane_model in self._lane_models:
            lane_model.insertRow(column)
        self.endInsertColumns()
        return True

    def removeColumn(self, column, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= column < self.columnCount()):
            return False
        self.beginRemoveColumns(parent, column, column)
        self._step_names_model.removeRow(column)
        self._step_durations_model.removeRow(column)
        for lane_model in self._lane_models:
            lane_model.removeRow(column)
        self.endRemoveColumns()
        return True

    def removeRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (2 <= row < self.rowCount()):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._lane_models[row - 2]
        self.endRemoveRows()

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        if not index.isValid():
            return []
        if index.row() >= 2:
            return self._lane_models[index.row() - 2].get_cell_context_actions(
                self._map_to_source(index)
            )

    def span(self, index):
        if not index.isValid():
            return QSize(1, 1)
        if index.row() >= 2:
            mapped_index = self._map_to_source(index)
            span = self._lane_models[index.row() - 2].span(mapped_index)
            return QSize(span.height(), span.width())
        return QSize(1, 1)

    def merge_lane_cells(self, lane_index: int, start: int, stop: int):
        lane_model = self._lane_models[lane_index]
        lane_model.merge_cells(start, stop)

    def _map_to_source(self, index: QModelIndex) -> QModelIndex:
        assert index.isValid()
        assert self.hasIndex(index.row(), index.column())
        if index.row() == 0:
            return self._step_names_model.index(index.column(), 0)
        elif index.row() == 1:
            return self._step_durations_model.index(index.column(), 0)
        else:
            return self._lane_models[index.row() - 2].index(index.column(), 0)

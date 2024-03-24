import abc
import copy
import functools
from collections.abc import Callable
from typing import Optional, Any, TypeVar, Generic

import caqtus.gui.common.qabc as qabc
from PySide6.QtCore import (
    QAbstractTableModel,
    QObject,
    QModelIndex,
    QAbstractListModel,
    Qt,
    QSize,
    QSettings,
)
from PySide6.QtGui import QAction, QBrush, QColor, QFont
from PySide6.QtWidgets import QMenu, QColorDialog
from caqtus.session.shot import TimeLane
from caqtus.session.shot.timelane import TimeLanes
from caqtus.types.expression import Expression


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

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return "Step names"
            elif orientation == Qt.Orientation.Vertical:
                return section
        elif role == Qt.ItemDataRole.FontRole:
            font = QFont()
            font.setBold(True)
            return font


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
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

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

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return "Step durations"
            elif orientation == Qt.Orientation.Vertical:
                return section
        elif role == Qt.ItemDataRole.FontRole:
            font = QFont()
            font.setBold(True)
            return font


T = TypeVar("T")
L = TypeVar("L", bound=TimeLane)
O = TypeVar("O", bound=Any)


class TimeLaneModel(QAbstractListModel, Generic[L, O], metaclass=qabc.QABCMeta):
    """An abstract list model to represent a time lane.

    This class is meant to be subclassed for each lane type that needs to be
    represented in the timelanes editor.
    Some common methods are implemented here, but subclasses will need to implement at
    least the abstract methods: :meth:`data`, :meth:`setData`, :meth:`insertRow`.
    In addition, subclasses may want to override :meth:`flags` to change the item flags
    for the cells in the lane.
    The :meth:`get_cell_context_actions` method can be overridden to add context menu
    actions to the cells in the lane.
    """

    def __init__(self, name: str, lane: L, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._name = name
        self._lane = lane

    def get_lane(self) -> L:
        """Return a copy of the lane represented by this model."""

        return copy.deepcopy(self._lane)

    def set_lane(self, lane: L) -> None:
        """Set the lane represented by this model."""

        self.beginResetModel()
        self._lane = copy.deepcopy(lane)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._lane)

    @abc.abstractmethod
    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        return None

    @abc.abstractmethod
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        raise NotImplementedError

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
        elif role == Qt.ItemDataRole.FontRole:
            font = QFont()
            font.setBold(True)
            return font

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsSelectable
        )

    @abc.abstractmethod
    def insertRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        raise NotImplementedError

    def insert_value(self, row: int, value: T) -> bool:
        if not (0 <= row <= len(self._lane)):
            return False
        self.beginInsertRows(QModelIndex(), row, row)
        start, stop = self._lane.get_bounds(row)
        self._lane.insert(row, value)
        if start < row < stop:
            self._lane[start : stop + 1] = self._lane[start]
        self.endInsertRows()
        return True

    def removeRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if not (0 <= row < len(self._lane)):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._lane[row]
        self.endRemoveRows()
        return True

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        break_span_action = QAction("Break block")
        break_span_action.triggered.connect(lambda: self.break_span(index))
        return [break_span_action]

    def span(self, index) -> QSize:
        start, stop = self._lane.get_bounds(index.row())
        if index.row() == start:
            return QSize(1, stop - start)
        else:
            return QSize(1, 1)

    def break_span(self, index: QModelIndex) -> bool:
        start, stop = self._lane.get_bounds(index.row())
        value = self._lane[index.row()]
        for i in range(start, stop):
            self._lane[i] = value
        self.dataChanged.emit(self.index(start), self.index(stop - 1))
        return True

    def expand_step(self, step: int, start: int, stop: int) -> None:
        value = self._lane[step]
        self._lane[start : stop + 1] = value
        self.dataChanged.emit(self.index(start), self.index(stop - 1))

    def get_header_context_actions(self) -> list[QAction | QMenu]:
        """Return a list of context menu actions for the lane header."""

        return []

    def simplify(self) -> None:
        """Simplify the lane by merging contiguous blocks of the same value."""

        self.beginResetModel()
        start = 0
        for i in range(1, len(self._lane)):
            if self._lane[i] != self._lane[start]:
                self._lane[start:i] = self._lane[start]
                start = i
        self._lane[start:] = self._lane[start]
        self.endResetModel()


class ColoredTimeLaneModel(TimeLaneModel[L, O], metaclass=qabc.QABCMeta):
    """A time lane model that can be colored.

    Instances of this class can be used to color the cells in a lane.
    They have the attribute :attr:`_brush` that is optionally a :class:`QBrush` that
    can be used to color the cells in the lane.
    """

    def __init__(self, name: str, lane: TimeLane, parent: Optional[QObject] = None):
        super().__init__(name, lane, parent)
        self._brush: Optional[QBrush] = None

        color = QSettings().value(f"lane color/{self._name}", None)
        if color is not None:
            self._brush = QBrush(color)
        else:
            self._brush = None

    @abc.abstractmethod
    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        """Returns its brush for the `Qt.ItemDataRole.ForegroundRole` role."""

        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._brush
        return super().data(index, role)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.ForegroundRole:
            return self._brush
        return super().headerData(section, orientation, role)

    def get_header_context_actions(self) -> list[QAction | QMenu]:
        action = QAction("Change color")
        action.triggered.connect(lambda: self._change_color())
        return [action]

    def _change_color(self):
        if self._brush is None:
            color = QColorDialog.getColor(title=f"Select color for {self._name}")
        else:
            color = QColorDialog.getColor(
                self._brush.color(), title=f"Select color for {self._name}"
            )
        if color.isValid():
            self.setHeaderData(
                0, Qt.Orientation.Horizontal, color, Qt.ItemDataRole.ForegroundRole
            )

    def setHeaderData(self, section, orientation, value, role=Qt.ItemDataRole.EditRole):
        change = False
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.ForegroundRole
        ):
            if isinstance(value, QColor):
                self._brush = QBrush(value)
                settings = QSettings()
                settings.setValue(f"lane color/{self._name}", value)
                change = True
            elif value is None:
                self._brush = None
                settings = QSettings()
                settings.remove(f"lane color/{self._name}")
                change = True
        if change:
            self.headerDataChanged.emit(orientation, section, section)
            return True

        return super().setHeaderData(section, orientation, value, role)


LaneModelFactory = Callable[[L], type[TimeLaneModel[L, Any]]]


class TimeLanesModel(QAbstractTableModel, metaclass=qabc.QABCMeta):
    def __init__(
        self, lane_model_factory: LaneModelFactory, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._step_names_model = TimeStepNameModel(self)
        self._step_durations_model = TimeStepDurationModel(self)
        self._lane_models: list[TimeLaneModel] = []
        self._lane_model_factory = lane_model_factory

        self._step_names_model.dataChanged.connect(self.on_step_names_data_changed)
        self._step_durations_model.dataChanged.connect(
            self.on_step_durations_data_changed
        )
        self._read_only = False

    def set_read_only(self, read_only: bool) -> None:
        self._read_only = read_only

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
        for index, (name, lane) in enumerate(timelanes.lanes.items()):
            lane_model = self.create_lane_model(name, lane)
            new_models.append(lane_model)

        self.beginResetModel()
        self._step_names_model.set_names(timelanes.step_names)
        self._step_durations_model.set_durations(timelanes.step_durations)
        self._lane_models.clear()
        self._lane_models.extend(new_models)
        self.endResetModel()

    def create_lane_model(self, name: str, lane: TimeLane) -> TimeLaneModel:
        lane_model = self._lane_model_factory(lane)(name, self)
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

    def insert_timelane(self, index: int, name: str, timelane: TimeLane):
        if self._read_only:
            return
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
        lane_model = self.create_lane_model(name, timelane)
        self.beginInsertRows(QModelIndex(), index, index)
        self._lane_models.insert(index, lane_model)
        self.endInsertRows()

    def get_lane(self, index: int) -> TimeLane:
        return self._lane_models[index].get_lane()

    def get_lane_name(self, index: int) -> str:
        return self._lane_models[index].headerData(0, Qt.Orientation.Horizontal)

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
        assert all(model.rowCount() == count for model in self._lane_models), [
            model.rowCount() for model in self._lane_models
        ]
        return count

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._lane_models) + 2

    def data(self, index, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        return self._map_to_source(index).data(role)

    def setData(self, index, value, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole):
        if self._read_only:
            return False
        if not index.isValid():
            return False
        mapped_index = self._map_to_source(index)
        return mapped_index.model().setData(mapped_index, value, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
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
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
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

    def insertColumn(self, column, parent: QModelIndex = QModelIndex()) -> bool:
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

    def removeColumn(self, column, parent: QModelIndex = QModelIndex()) -> bool:
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

    def removeRow(self, row, parent: QModelIndex = QModelIndex()) -> bool:
        if self._read_only:
            return False
        if not (2 <= row < self.rowCount()):
            return False
        self.beginRemoveRows(parent, row, row)
        del self._lane_models[row - 2]
        self.endRemoveRows()

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

    def _map_to_source(self, index: QModelIndex) -> QModelIndex:
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

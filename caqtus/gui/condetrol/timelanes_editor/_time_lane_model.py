import abc
import copy
from typing import Optional, Any, TypeVar, Generic, TYPE_CHECKING

from PySide6.QtCore import (
    QObject,
    QModelIndex,
    QAbstractListModel,
    Qt,
    QSize,
    QSettings,
)
from PySide6.QtGui import QAction, QBrush, QColor, QFont
from PySide6.QtWidgets import QMenu, QColorDialog

import caqtus.gui.qtutil.qabc as qabc
from caqtus.types.timelane import TimeLane, Step

if TYPE_CHECKING:
    pass

T = TypeVar("T")
L = TypeVar("L", bound=TimeLane)

_DEFAULT_INDEX = QModelIndex()


class TimeLaneModel(QAbstractListModel, Generic[L], metaclass=qabc.QABCMeta):
    """An abstract list model to represent a time lane.

    This class inherits from :class:`PySide6.QtCore.QAbstractListModel` and can be
    used to represent a lane in the timelanes editor.

    It is meant to be subclassed for each lane type that needs to be represented in
    the timelanes editor.
    Some common methods are implemented here, but subclasses will need to implement at
    least the abstract methods: :meth:`data`, :meth:`setData`, :meth:`insertRow`.
    In addition, subclasses may want to override :meth:`flags` to change the item flags
    for the cells in the lane.
    The :meth:`get_cell_context_actions` method can be overridden to add context menu
    actions to the cells in the lane.
    """

    # Ignore some lint rules for this file as PySide6 models have a lot of camelCase
    # methods.
    # ruff: noqa: N802

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

    def rowCount(self, parent=_DEFAULT_INDEX) -> int:
        """Return the number of steps in the lane."""

        return len(self._lane)

    @abc.abstractmethod
    def data(self, index, role=Qt.ItemDataRole.DisplayRole) -> Any:
        """Return the data for the given index and role.

        See :meth:`PySide6.QtCore.QAbstractItemModel.data` for more information.
        """

        return None

    @abc.abstractmethod
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        """Set the data for the given index and role.

        See :meth:`PySide6.QtCore.QAbstractItemModel.setData` for more information.
        """

        raise NotImplementedError

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role=Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._name
            elif orientation == Qt.Orientation.Vertical:
                return section
        elif role == Qt.ItemDataRole.FontRole:
            font = QFont()
            font.setBold(True)
            return font

    def flags(self, index) -> Qt.ItemFlag:
        """Return the flags for the given index.

        By default, the flags are set to `ItemIsEnabled`, `ItemIsEditable`, and
        `ItemIsSelectable`.
        """

        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsSelectable
        )

    @abc.abstractmethod
    def insertRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        raise NotImplementedError

    def insert_value(self, row: int, value: Any) -> bool:
        if not (0 <= row <= len(self._lane)):
            return False
        self.beginInsertRows(QModelIndex(), row, row)
        if row == len(self._lane):
            self._lane.append(value)
        else:
            start, stop = self._lane.get_bounds(Step(row))
            self._lane.insert(row, value)
            if start < row < stop:
                self._lane[start : stop + 1] = self._lane[start]
        self.endInsertRows()
        return True

    def removeRow(self, row, parent=_DEFAULT_INDEX) -> bool:
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
        start, stop = self._lane.get_bounds(Step(index.row()))
        if index.row() == start:
            return QSize(1, stop - start)
        else:
            return QSize(1, 1)

    def break_span(self, index: QModelIndex) -> bool:
        start, stop = self._lane.get_bounds(Step(index.row()))
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


class ColoredTimeLaneModel(TimeLaneModel[L], metaclass=qabc.QABCMeta):
    """A time lane model that can be colored.

    Instances of this class can be used to color the cells in a lane.
    They have the attribute :attr:`_brush` that is optionally a :class:`QBrush` that
    can be used to color the cells in the lane.
    """

    def __init__(self, name: str, lane: L, parent: Optional[QObject] = None):
        super().__init__(name, lane, parent)
        self._brush: Optional[QBrush] = None

        color = QSettings().value(f"lane color/{self._name}", None)
        if color is not None:
            self._brush = QBrush(color)
        else:
            self._brush = None

    @abc.abstractmethod
    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
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
        role: int = Qt.ItemDataRole.DisplayRole,
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

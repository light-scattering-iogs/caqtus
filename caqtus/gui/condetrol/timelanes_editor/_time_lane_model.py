from __future__ import annotations

import abc
import copy
from typing import Optional, Any, TypeVar

import attrs
from PySide6.QtCore import (
    QObject,
    QModelIndex,
    QAbstractListModel,
    Qt,
    QSize,
    QPersistentModelIndex,
)
from PySide6.QtGui import QAction, QFont, QUndoCommand, QUndoStack
from PySide6.QtWidgets import QMenu

import caqtus.gui.qtutil.qabc as qabc
from caqtus.types.timelane import TimeLane, Step

T = TypeVar("T")
L = TypeVar("L", bound=TimeLane)

_DEFAULT_INDEX = QModelIndex()


class TimeLaneModel[L: TimeLane](QAbstractListModel, metaclass=qabc.QABCMeta):
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

    Warning:
        All user edits to the data model should be done through the undo stack of
        the model.

    """

    # Ignore some lint rules for this class as PySide6 models have a lot of camelCase
    # methods.
    # ruff: noqa: N802

    def __init__(
        self,
        name: str,
        lane: L,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.__name = name
        self.__lane: L = lane
        self.__undo_stack = QUndoStack(self)

    def set_undo_stack(self, undo_stack: QUndoStack) -> None:
        """Set the undo stack for the model."""

        self.__undo_stack = undo_stack

    def name(self) -> str:
        """Return the name of the lane represented by this model."""

        return self.__name

    def get_lane(self) -> L:
        """Return a copy of the lane represented by this model."""

        return copy.deepcopy(self.__lane)

    def set_lane[
        L_contra: TimeLane
    ](self: TimeLaneModel[L_contra], lane: L_contra) -> None:
        """Set the lane represented by this model.

        This method does not push changes to the undo stack.
        """

        self.beginResetModel()
        self.__lane = copy.deepcopy(lane)
        self.endResetModel()

    def rowCount(self, parent=_DEFAULT_INDEX) -> int:
        """Return the number of steps in the lane."""

        return len(self.__lane)

    @abc.abstractmethod
    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role=Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return the data to be shown to the user for the given index and role.

        See :meth:`PySide6.QtCore.QAbstractItemModel.data` for more information on the
        roles that can be used.

        This method must be implemented by subclasses, typically by calling the
        :meth:`lane_value` method and returning the appropriate value for the given
        role.
        """

        return None

    def lane_value[T](self: TimeLaneModel[TimeLane[T]], step: int) -> T:
        """Return the value of the underlying lane at the given step."""

        return self.__lane[step]

    @abc.abstractmethod
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        """Set the data for the given index and role.

        See :meth:`PySide6.QtCore.QAbstractItemModel.setData` for more information on
        the roles that can be used.

        This method must be implemented by subclasses, typically by calling the
        :meth:`set_lane_value` method with an adequate value.
        """

        raise NotImplementedError

    def set_lane_value[
        T
    ](self: TimeLaneModel[TimeLane[T]], step: int, value: T) -> bool:
        """Set the value of the underlying lane at the given step.

        The value of the whole block the step is part of is set to the new value.

        The change is pushed to the undo stack.

        Returns:
            True if the value was set successfully, False otherwise.
        """

        if not (0 <= step < len(self.__lane)):
            return False
        self.__undo_stack.push(
            self.SetValueCommand(
                model=self,
                step=step,
                previous_value=self.lane_value(step),
                new_value=value,
            )
        )
        return True

    @attrs.define(slots=False, kw_only=True)
    class SetValueCommand(QUndoCommand):
        """An undo/redo command to set the value of a step in a time lane model."""

        model: TimeLaneModel
        step: int
        previous_value: Any
        new_value: Any

        def __attrs_post_init__(self):
            super().__init__(
                f"change value for Step {self.step} of {self.model.name()} from "
                f"<{self.previous_value}> to <{self.new_value}>"
            )

        def redo(self):
            self.model._set_value_without_undo(self.step, self.new_value)

        def undo(self):
            self.model._set_value_without_undo(self.step, self.previous_value)

    def _set_value_without_undo[
        T
    ](self: TimeLaneModel[TimeLane[T]], step: int, value: T) -> None:
        """Set the value of the underlying lane without pushing an undo command.

        The step must be a valid index for the lane.
        The value of the whole block the step is part of is set to the new value.
        """

        assert 0 <= step < len(self.__lane)
        start, stop = self.__lane.get_bounds(Step(step))
        self.__lane[start:stop] = value
        self.dataChanged.emit(self.index(step), self.index(step))

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role=Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return the data for the model header."""

        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.name()
            elif orientation == Qt.Orientation.Vertical:
                return f"Step {section}"
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
    def insertRow(self, row: int, parent=_DEFAULT_INDEX) -> bool:
        """Insert a row at the given row index.

        This method must be implemented by subclasses, typically by calling the
        :meth:`insert_lane_value` method with an adequate value.
        """

        raise NotImplementedError

    def insert_lane_value[
        T
    ](self: TimeLaneModel[TimeLane[T]], step: int, value: T) -> bool:
        """Insert a value at the given row index.

        The action is pushed to the undo stack.
        """

        if not (0 <= step <= len(self.__lane)):
            return False
        self.__undo_stack.push(
            self.InsertValueCommand(model=self, step=step, new_value=value)
        )
        return True

    @attrs.define(slots=False)
    class InsertValueCommand(QUndoCommand):
        model: TimeLaneModel
        step: int
        new_value: Any

        def __attrs_post_init__(self):
            super().__init__(f"insert step {self.step}")

        def redo(self):
            self.model._insert_lane_value_without_undo(self.step, self.new_value)

        def undo(self):
            self.model._remove_step_without_undo(self.step)

    def _insert_lane_value_without_undo[
        T
    ](self: TimeLaneModel[TimeLane[T]], step: int, value: T) -> None:
        """Insert a value at the given row index without pushing an undo command.

        The step must be a valid index for the lane.
        """

        assert 0 <= step <= len(self.__lane)
        self.beginInsertRows(QModelIndex(), step, step)
        if step == len(self.__lane):
            self.__lane.append(value)
        else:
            start, stop = self.__lane.get_bounds(Step(step))
            self.__lane.insert(step, value)
            if start < step < stop:
                self.__lane[start : stop + 1] = self.__lane[start]
        self.endInsertRows()

    def removeRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        """Remove a row at the given row index.

        The action is pushed to the undo stack.
        """

        if not (0 <= row < len(self.__lane)):
            return False

        start, stop = self.__lane.get_bounds(Step(row))
        self.__undo_stack.push(
            self.RemoveStepCommand(
                model=self, step=row, value=self.lane_value(row), start=start, stop=stop
            )
        )
        return True

    @attrs.define(slots=False)
    class RemoveStepCommand(QUndoCommand):
        model: TimeLaneModel
        step: int
        value: Any
        start: int
        stop: int

        def __attrs_post_init__(self):
            super().__init__(f"remove step {self.step}")

        def redo(self):
            self.model._remove_step_without_undo(self.step)

        def undo(self):
            self.model._reinsert_step_without_undo(
                self.step, self.value, self.start, self.stop
            )

    def _remove_step_without_undo(self, step: int) -> None:
        """Remove a step at the given row index without pushing an undo command.

        The step must be a valid index for the lane.
        """

        assert 0 <= step < len(self.__lane)
        self.beginRemoveRows(QModelIndex(), step, step)
        del self.__lane[step]
        self.endRemoveRows()

    def _reinsert_step_without_undo(
        self, step: int, value, start: int, stop: int
    ) -> None:
        assert 0 <= step <= len(self.__lane)
        self.beginInsertRows(QModelIndex(), step, step)
        self._insert_lane_value_without_undo(step, value)
        self._expand_step_without_undo(step, start, stop - 1)
        self.endInsertRows()

    def get_cell_context_actions(self, index: QModelIndex) -> list[QAction | QMenu]:
        break_span_action = QAction("Break block")
        break_span_action.triggered.connect(lambda: self.break_span(index))
        return [break_span_action]

    def span(self, index) -> QSize:
        """Return the span of the cell at the given index."""

        start, stop = self.__lane.get_bounds(Step(index.row()))
        if index.row() == start:
            return QSize(1, stop - start)
        else:
            return QSize(1, 1)

    def break_span(self, index: QModelIndex) -> bool:
        """Break the block of the cell at the given index.

        The action is pushed to the undo stack.
        """

        start, stop = self.__lane.get_bounds(Step(index.row()))
        self.__undo_stack.push(
            self.BreakSpanCommand(model=self, step=index.row(), start=start, stop=stop)
        )

        value = self.__lane[index.row()]
        for i in range(start, stop):
            self.__lane[i] = value
        self.dataChanged.emit(self.index(start), self.index(stop - 1))
        return True

    @attrs.define(slots=False)
    class BreakSpanCommand(QUndoCommand):
        model: TimeLaneModel
        step: int
        start: int
        stop: int

        def __attrs_post_init__(self):
            super().__init__(f"break span at step {self.step}")

        def redo(self):
            self.model._break_span_without_undo(self.step, self.start, self.stop)

        def undo(self):
            self.model._expand_step_without_undo(self.step, self.start, self.stop)

    def _break_span_without_undo(self, step: int, start: int, stop: int) -> None:
        value = self.__lane[step]
        for i in range(start, stop):
            self.__lane[i] = value
        self.dataChanged.emit(self.index(start), self.index(stop - 1))

    def expand_step(self, step: int, start: int, stop: int) -> bool:
        """Expand the step at the given index to the given range.

        The action is pushed to the undo stack.
        """

        if not (0 <= step < len(self.__lane)):
            return False
        self.__undo_stack.push(
            self.ExpandStepCommand(model=self, step=step, start=start, stop=stop)
        )
        return True

    @attrs.define(slots=False)
    class ExpandStepCommand(QUndoCommand):
        model: TimeLaneModel
        step: int
        start: int
        stop: int

        def __attrs_post_init__(self):
            super().__init__(f"expand step at step {self.step}")

        def redo(self):
            self.model._expand_step_without_undo(self.step, self.start, self.stop)

        def undo(self):
            self.model._break_span_without_undo(self.step, self.start, self.stop)

    def _expand_step_without_undo(self, step: int, start: int, stop: int) -> None:
        value = self.__lane[step]
        self.__lane[start : stop + 1] = value
        self.dataChanged.emit(self.index(start), self.index(stop - 1))

    def get_header_context_actions(self) -> list[QAction | QMenu]:
        """Return a list of context menu actions for the lane header."""

        return []

    def simplify(self) -> None:
        """Simplify the lane by merging contiguous blocks of the same value.

        The action is pushed to the undo stack.
        """

        self.__undo_stack.push(
            self.SimplifyCommand(model=self, lane=copy.deepcopy(self.__lane))
        )

    @attrs.define(slots=False)
    class SimplifyCommand(QUndoCommand):
        model: TimeLaneModel
        lane: TimeLane

        def __attrs_post_init__(self):
            super().__init__("simplify lane")

        def redo(self):
            self.model._simplify_without_undo()

        def undo(self):
            self.model.beginResetModel()
            self.model.set_lane(self.lane)
            self.model.endResetModel()

    def _simplify_without_undo(self) -> None:
        self.beginResetModel()
        start = 0
        for i in range(1, len(self.__lane)):
            if self.__lane[i] != self.__lane[start]:
                self.__lane[start:i] = self.__lane[start]
                start = i
        self.__lane[start:] = self.__lane[start]
        self.endResetModel()

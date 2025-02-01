# Ignore some lint rules for this file as PySide6 models have a lot of camelCase
# methods.
# ruff: noqa: N802
from __future__ import annotations

import copy
from typing import Optional

import attrs
from PySide6.QtCore import (
    QAbstractListModel,
    QObject,
    QModelIndex,
    Qt,
)
from PySide6.QtGui import QFont, QUndoCommand, QUndoStack

from caqtus.types.expression import Expression

_DEFAULT_INDEX = QModelIndex()


class TimeStepNameModel(QAbstractListModel):
    def __init__(self, undo_stak: QUndoStack, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._names: list[str] = []
        self._undo_stack = undo_stak

    def set_names(self, names: list[str]):
        self.beginResetModel()
        self._names = copy.deepcopy(names)
        self.endResetModel()

    def get_names(self) -> list[str]:
        """Return a copy of the names displayed in the model."""

        return copy.deepcopy(self._names)

    def rowCount(self, parent=_DEFAULT_INDEX) -> int:
        return len(self._names)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
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
            self._undo_stack.push(
                self.SetDataCommand(self, index.row(), self._names[index.row()], value)
            )
            return True
        return False

    @attrs.define(slots=False)
    class SetDataCommand(QUndoCommand):
        model: TimeStepNameModel
        row: int
        previous_value: str
        new_value: str

        def __attrs_post_init__(self):
            super().__init__(
                f"change name of Step 1 from <{self.previous_value}> to "
                f"<{self.new_value}>"
            )

        def redo(self) -> None:
            self.model._names[self.row] = self.new_value
            self.model.dataChanged.emit(
                self.model.index(self.row), self.model.index(self.row)
            )

        def undo(self) -> None:
            self.model._names[self.row] = self.previous_value
            self.model.dataChanged.emit(
                self.model.index(self.row), self.model.index(self.row)
            )

    def flags(self, index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def insertRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        if not (0 <= row <= self.rowCount()):
            return False
        self._undo_stack.push(self._InsertStepCommand(self, row))
        return True

    @attrs.define(slots=False)
    class _InsertStepCommand(QUndoCommand):
        model: TimeStepNameModel
        step: int

        def __attrs_post_init__(self):
            super().__init__(f"insert step {self.step}")

        def redo(self) -> None:
            self.model._insert_row_without_undo(self.step, f"Step {self.step}")

        def undo(self) -> None:
            self.model._remove_row_without_undo(self.step)

    def _insert_row_without_undo(self, row, value: str) -> None:
        assert 0 <= row <= self.rowCount()
        self.beginInsertRows(_DEFAULT_INDEX, row, row)
        self._names.insert(row, value)
        self.endInsertRows()

    def removeRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        if not (0 <= row < self.rowCount()):
            return False
        self._undo_stack.push(self._RemoveStepCommand(self, row, self._names[row]))
        return True

    @attrs.define(slots=False)
    class _RemoveStepCommand(QUndoCommand):
        model: TimeStepNameModel
        step: int
        value: str

        def __attrs_post_init__(self):
            super().__init__(f"remove step {self.step}")

        def redo(self) -> None:
            self.model._remove_row_without_undo(self.step)

        def undo(self) -> None:
            self.model._insert_row_without_undo(self.step, self.value)

    def _remove_row_without_undo(self, row) -> None:
        assert 0 <= row < self.rowCount()
        self.beginRemoveRows(_DEFAULT_INDEX, row, row)
        del self._names[row]
        self.endRemoveRows()

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
    def __init__(self, undo_stack: QUndoStack, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._durations: list[Expression] = []
        self._undo_stack = undo_stack

    def set_durations(self, durations: list[Expression]):
        self.beginResetModel()
        self._durations = copy.deepcopy(durations)
        self.endResetModel()

    def get_duration(self) -> list[Expression]:
        return copy.deepcopy(self._durations)

    def rowCount(self, parent=_DEFAULT_INDEX) -> int:
        return len(self._durations)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
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
            self._undo_stack.push(
                self.SetDataCommand(
                    self, index.row(), self._durations[index.row()], Expression(value)
                )
            )
            return True
        return False

    @attrs.define(slots=False)
    class SetDataCommand(QUndoCommand):
        model: TimeStepDurationModel
        row: int
        previous_value: Expression
        new_value: Expression

        def __attrs_post_init__(self):
            super().__init__(
                f"change duration of Step 1 from <{self.previous_value}> to "
                f"<{self.new_value}>"
            )

        def redo(self) -> None:
            self.model._durations[self.row] = self.new_value
            self.model.dataChanged.emit(
                self.model.index(self.row), self.model.index(self.row)
            )

        def undo(self) -> None:
            self.model._durations[self.row] = self.previous_value
            self.model.dataChanged.emit(
                self.model.index(self.row), self.model.index(self.row)
            )

    def flags(self, index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def insertRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        if not (0 <= row <= self.rowCount()):
            return False
        self._undo_stack.push(self._InsertStepCommand(self, row))
        return True

    @attrs.define(slots=False)
    class _InsertStepCommand(QUndoCommand):
        model: TimeStepDurationModel
        step: int

        def __attrs_post_init__(self):
            super().__init__(f"insert step {self.step}")

        def redo(self) -> None:
            self.model._insert_row_without_undo(self.step, Expression("..."))

        def undo(self) -> None:
            self.model._remove_row_without_undo(self.step)

    def _insert_row_without_undo(self, row, value: Expression) -> None:
        assert 0 <= row <= self.rowCount()
        self.beginInsertRows(_DEFAULT_INDEX, row, row)
        self._durations.insert(row, value)
        self.endInsertRows()

    def removeRow(self, row, parent=_DEFAULT_INDEX) -> bool:
        if not (0 <= row < self.rowCount()):
            return False
        self._undo_stack.push(self._RemoveStepCommand(self, row, self._durations[row]))
        return True

    @attrs.define(slots=False)
    class _RemoveStepCommand(QUndoCommand):
        model: TimeStepDurationModel
        step: int
        value: Expression

        def __attrs_post_init__(self):
            super().__init__(f"remove step {self.step}")

        def redo(self) -> None:
            self.model._remove_row_without_undo(self.step)

        def undo(self) -> None:
            self.model._insert_row_without_undo(self.step, self.value)

    def _remove_row_without_undo(self, row) -> None:
        assert 0 <= row < self.rowCount()
        self.beginRemoveRows(_DEFAULT_INDEX, row, row)
        del self._durations[row]
        self.endRemoveRows()

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

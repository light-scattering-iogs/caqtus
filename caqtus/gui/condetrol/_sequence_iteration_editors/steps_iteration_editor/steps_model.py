from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Optional, Any

import attrs
from PySide6.QtCore import (
    QModelIndex,
    Qt,
    QObject,
    QMimeData,
    QPersistentModelIndex,
)
from PySide6.QtGui import (
    QStandardItem,
    QStandardItemModel,
    QPalette,
    QUndoStack,
    QUndoCommand,
)

from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    StepsConfiguration,
    Step,
    ExecuteShot,
    VariableDeclaration,
    LinspaceLoop,
    ArangeLoop,
)
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization

NAME_COLOR = "#AA4926"
VALUE_COLOR = "#6897BB"
HIGHLIGHT_COLOR = "#cc7832"

type AnyModelIndex = QModelIndex | QPersistentModelIndex

DEFAULT_INDEX = QModelIndex()


@attrs.define
class ExecuteShotData:
    def display_data(self) -> str:
        return f"<span style='color:{HIGHLIGHT_COLOR}'>do shot</span>"


@attrs.define
class VariableDeclarationData:
    variable: DottedVariableName
    value: Expression

    def display_data(self) -> str:
        text_color = f"#{QPalette().text().color().rgba():X}"
        return (
            f"<span style='color:{NAME_COLOR}'>{self.variable}</span> "
            f"<span style='color:{text_color}'>=</span> "
            f"<span style='color:{VALUE_COLOR}'>{self.value}</span>"
        )


@attrs.define
class LinspaceLoopData:
    variable: DottedVariableName
    start: Expression
    stop: Expression
    num: int

    def display_data(self) -> str:
        text_color = f"#{QPalette().text().color().rgba():X}"
        return (
            f"<span style='color:{HIGHLIGHT_COLOR}'>for</span> "
            f"<span style='color:{NAME_COLOR}'>{self.variable}</span> "
            f"<span style='color:{text_color}'>=</span> "
            f"<span style='color:{VALUE_COLOR}'>{self.start}</span> "
            f"<span style='color:{HIGHLIGHT_COLOR}'>to </span> "
            f"<span style='color:{VALUE_COLOR}'>{self.stop}</span> "
            f"<span style='color:{HIGHLIGHT_COLOR}'>with </span> "
            f"<span style='color:{VALUE_COLOR}'>{self.num}</span> "
            f"<span style='color:{HIGHLIGHT_COLOR}'>steps:</span>"
        )


@attrs.define
class ArrangeLoopData:
    variable: DottedVariableName
    start: Expression
    stop: Expression
    step: Expression

    def display_data(self) -> str:
        text_color = f"#{QPalette().text().color().rgba():X}"
        return (
            f"<span style='color:{HIGHLIGHT_COLOR}'>for</span> "
            f"<span style='color:{NAME_COLOR}'>{self.variable}</span> "
            f"<span style='color:{text_color}'>=</span> "
            f"<span style='color:{VALUE_COLOR}'>{self.start}</span> "
            f"<span style='color:{HIGHLIGHT_COLOR}'>to </span> "
            f"<span style='color:{VALUE_COLOR}'>{self.stop}</span> "
            f"<span style='color:{HIGHLIGHT_COLOR}'>with </span> "
            f"<span style='color:{VALUE_COLOR}'>{self.step}</span> "
            f"<span style='color:{HIGHLIGHT_COLOR}'>spacing:</span>"
        )


StepData = (
    ExecuteShotData | VariableDeclarationData | LinspaceLoopData | ArrangeLoopData
)


class StepItem(QStandardItem):
    @classmethod
    def construct(cls, step: Step) -> StepItem:
        item = cls()
        flags = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        match step:
            case ExecuteShot():
                item.setData(ExecuteShotData(), Qt.ItemDataRole.EditRole)
                item.setFlags(flags | Qt.ItemFlag.ItemNeverHasChildren)
            case VariableDeclaration(variable=variable, value=value):
                item.setData(
                    VariableDeclarationData(variable=variable, value=value),
                    Qt.ItemDataRole.EditRole,
                )
                item.setFlags(
                    flags
                    | Qt.ItemFlag.ItemIsEditable
                    | Qt.ItemFlag.ItemNeverHasChildren
                )
            case LinspaceLoop(
                variable=variable, start=start, stop=stop, num=num, sub_steps=sub_steps
            ):
                children = [cls.construct(sub_step) for sub_step in sub_steps]
                item.setData(
                    LinspaceLoopData(
                        variable=variable, start=start, stop=stop, num=num
                    ),
                    Qt.ItemDataRole.EditRole,
                )
                for child in children:
                    item.appendRow(child)
                item.setFlags(
                    flags | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDropEnabled
                )
            case ArangeLoop(
                variable=variable,
                start=start,
                stop=stop,
                step=loop_step,
                sub_steps=sub_steps,
            ):
                children = [cls.construct(sub_step) for sub_step in sub_steps]
                item.setData(
                    ArrangeLoopData(
                        variable=variable, start=start, stop=stop, step=loop_step
                    ),
                    Qt.ItemDataRole.EditRole,
                )
                for child in children:
                    item.appendRow(child)
                item.setFlags(
                    flags | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDropEnabled
                )
            case _:
                raise NotImplementedError(f"Step {step} not supported")

        return item

    def data(self, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            step_data = self.data(Qt.ItemDataRole.EditRole)
            assert isinstance(step_data, StepData)
            return step_data.display_data()
        return super().data(role)

    def child(self, row: int, column: int | None = 0) -> StepItem:
        result = super().child(row, column)
        assert isinstance(result, StepItem)
        return result

    def get_step(self) -> Step:
        """Return a copy of the step represented by this item."""

        data = self.data(role=Qt.ItemDataRole.EditRole)
        match data:
            case ExecuteShotData():
                return ExecuteShot()
            case VariableDeclarationData(variable=variable, value=value):
                return VariableDeclaration(variable=variable, value=value)
            case LinspaceLoopData(variable=variable, start=start, stop=stop, num=num):
                child_items = [self.child(i) for i in range(self.rowCount())]
                sub_steps = [item.get_step() for item in child_items]
                return LinspaceLoop(
                    variable=variable,
                    start=start,
                    stop=stop,
                    num=num,
                    sub_steps=sub_steps,
                )
            case ArrangeLoopData(variable=variable, start=start, stop=stop, step=step):
                child_items = [self.child(i) for i in range(self.rowCount())]
                sub_steps = [item.get_step() for item in child_items]
                return ArangeLoop(
                    variable=variable,
                    start=start,
                    stop=stop,
                    step=step,
                    sub_steps=sub_steps,
                )
            case _:
                raise NotImplementedError(f"Step {data} not supported")


class StepsModel(QStandardItemModel):
    """Tree model for the steps of a sequence.

    This model holds an undo stack to allow undoing and redoing changes to the steps.
    """

    # ruff: noqa: N802

    def __init__(self, steps: StepsConfiguration, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._read_only = True
        self.undo_stack = QUndoStack(self)
        self.undo_stack.setClean()
        self.set_steps(steps)

    def set_read_only(self, read_only: bool):
        self._read_only = read_only

    def is_read_only(self) -> bool:
        return self._read_only

    def get_steps(self) -> StepsConfiguration:
        root = self.invisibleRootItem()
        items = [root.child(i) for i in range(root.rowCount())]
        steps = []
        for item in items:
            assert isinstance(item, StepItem)
            steps.append(item.get_step())
        return StepsConfiguration(steps=steps)

    def set_steps(self, steps: StepsConfiguration):
        """Reset the steps contained in the model.

        This mehod clears the undo stack of the model.
        """

        self.beginResetModel()
        self.undo_stack.clear()
        self.clear()
        items = [StepItem.construct(step) for step in steps.steps]
        root = self.invisibleRootItem()
        for item in items:
            root.appendRow(item)
        self.endResetModel()

    def setData(self, index, value, role: int = Qt.ItemDataRole.EditRole):
        if self._read_only:
            return False
        previous_value = index.data(role)
        if previous_value == value:
            return False
        flat_index = into_flat_index(index)
        self.undo_stack.push(
            self.SetDataCommand(
                model=self,
                index=flat_index,
                previous_value=previous_value,
                new_value=value,
            )
        )
        return True

    @attrs.define(slots=False)
    class SetDataCommand(QUndoCommand):
        model: StepsModel
        index: FlatIndex
        previous_value: Any
        new_value: Any

        def __attrs_post_init__(self):
            super().__init__("change step value")

        def redo(self):
            index = self.model.into_index(self.index)
            QStandardItemModel.setData(
                self.model, index, self.new_value, Qt.ItemDataRole.EditRole
            )

        def undo(self):
            index = self.model.into_index(self.index)
            QStandardItemModel.setData(
                self.model, index, self.previous_value, Qt.ItemDataRole.EditRole
            )

    def flags(self, index: AnyModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)

        if self._read_only:
            flags &= ~Qt.ItemFlag.ItemIsEditable
            flags &= ~Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return ["application/json"]

    def mimeData(self, indexes: Iterable[QModelIndex]) -> QMimeData:
        items = [self.itemFromIndex(index) for index in indexes]
        assert all(isinstance(item, StepItem) for item in items)
        descendants = []
        for item in items:
            descendants.extend(get_strict_descendants(item))
        items = [item for item in items if item not in descendants]

        steps = [item.get_step() for item in items]
        serialized = serialization.to_json(steps)
        mime_data = QMimeData()
        mime_data.setData("application/json", serialized.encode())
        mime_data.setText(serialized)
        return mime_data

    def itemFromIndex(self, index: AnyModelIndex) -> StepItem:
        result = super().itemFromIndex(index)
        assert isinstance(result, StepItem)
        return result

    def canDropMimeData(
        self,
        data,
        action,
        row: int,
        column: int,
        parent: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        if self._read_only:
            return False
        if not data.hasFormat("application/json"):
            return False
        return super().canDropMimeData(data, action, row, column, parent)

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        if not self.canDropMimeData(data, action, row, column, parent):
            return False

        bytes_data = data.data("application/json").data()
        assert isinstance(bytes_data, bytes)
        json_string = bytes_data.decode()
        try:
            steps = serialization.from_json(json_string, list[Step])
        except ValueError:
            return False

        parent_item = (
            self.itemFromIndex(parent) if parent.isValid() else self.invisibleRootItem()
        )
        if not (parent_item.flags() & Qt.ItemFlag.ItemIsDropEnabled):
            return False
        if row == -1:
            row = parent_item.rowCount()
        self.undo_stack.push(
            self.InsertStepsCommand(
                model=self, steps=tuple(steps), parent=into_flat_index(parent), row=row
            )
        )
        return True

    @attrs.define(slots=False)
    class InsertStepsCommand(QUndoCommand):
        model: StepsModel
        steps: tuple[Step, ...]
        parent: FlatIndex
        row: int

        def __attrs_post_init__(self):
            step_text = ", ".join(f"<{step}>" for step in self.steps)
            super().__init__(f"insert {step_text}")

        def redo(self):
            parent = self.model.into_index(self.parent)
            self.model._insert_steps_without_undo(self.steps, self.row, parent)

        def undo(self):
            parent_index = self.model.into_index(self.parent)
            parent_item = (
                self.model.itemFromIndex(parent_index)
                if parent_index.isValid()
                else self.model.invisibleRootItem()
            )
            parent_item.removeRows(self.row, len(self.steps))

    def insert_steps(
        self, steps: Sequence[Step], row: int, parent: QModelIndex
    ) -> bool:
        """Insert steps at the given row under the given parent.

        This method pushes an undo command to the undo stack of the model.
        """

        if self._read_only:
            return False
        self.undo_stack.push(
            self.InsertStepsCommand(
                model=self, steps=tuple(steps), parent=into_flat_index(parent), row=row
            )
        )
        return True

    def _insert_steps_without_undo(
        self, steps: Sequence[Step], row: int, parent: QModelIndex
    ) -> bool:
        if self._read_only:
            return False
        parent_item = (
            self.itemFromIndex(parent) if parent.isValid() else self.invisibleRootItem()
        )
        new_items = [StepItem.construct(step) for step in steps]
        parent_item.insertRows(row, new_items)
        return True

    def removeRow(
        self, row, parent: QModelIndex | QPersistentModelIndex = DEFAULT_INDEX
    ) -> bool:
        return self.removeRows(row, 1, parent)

    def into_index(self, flat_index: FlatIndex) -> QModelIndex:
        index = QModelIndex()
        for row in flat_index.rows:
            index = self.index(row, 0, index)
        return index

    def removeRows(
        self, row, count, parent: QModelIndex | QPersistentModelIndex = DEFAULT_INDEX
    ) -> bool:
        if self._read_only:
            return False
        items = [
            self.itemFromIndex(self.index(row + i, 0, parent)) for i in range(count)
        ]
        steps = tuple(item.get_step() for item in items)

        self.undo_stack.push(
            self.RemoveRowsCommand(self, steps, row, into_flat_index(parent))
        )
        return True

    def remove_indices(
        self, indices: Sequence[QModelIndex | QPersistentModelIndex]
    ) -> bool:
        if self._read_only:
            return False
        # Need to be careful that the indexes are not invalidated by the removal of
        # previous rows, that's why we convert them to QPersistentModelIndex.
        persistent_indices = [
            QPersistentModelIndex(index) for index in indices if index.isValid()
        ]
        if not persistent_indices:
            return False
        self.undo_stack.beginMacro("remove steps")
        for index in persistent_indices:
            self.removeRow(index.row(), index.parent())
        self.undo_stack.endMacro()
        return True

    @attrs.define(slots=False)
    class RemoveRowsCommand(QUndoCommand):
        model: StepsModel
        steps: tuple[Step, ...]
        row: int
        parent: FlatIndex

        def __attrs_post_init__(self):
            super().__init__("remove steps")

        def redo(self):
            parent_index = self.model.into_index(self.parent)
            QStandardItemModel.removeRows(
                self.model, self.row, len(self.steps), parent_index
            )

        def undo(self):
            parent = self.model.into_index(self.parent)
            result = self.model._insert_steps_without_undo(self.steps, self.row, parent)
            assert result

    def replace_steps(self, steps: Sequence[Step], message: str) -> bool:
        if self._read_only:
            return False
        self.undo_stack.beginMacro(message)
        self.removeRows(0, self.rowCount())
        self.insert_steps(steps, 0, QModelIndex())
        self.undo_stack.endMacro()
        return True


@attrs.frozen
class FlatIndex:
    rows: tuple[int, ...]

    def parent(self) -> FlatIndex:
        if not self.rows:
            raise ValueError("Cannot get parent of root index")
        return FlatIndex(self.rows[:-1])

    def row(self) -> int:
        if not self.rows:
            raise ValueError("Cannot get row of root index")
        return self.rows[-1]


def into_flat_index(index: QModelIndex | QPersistentModelIndex) -> FlatIndex:
    rows = []
    while index.isValid():
        rows.append(index.row())
        index = index.parent()
    return FlatIndex(tuple(rows[::-1]))


def get_strict_descendants(parent: QStandardItem) -> list[QStandardItem]:
    children = [parent.child(i) for i in range(parent.rowCount())]
    descendants = []
    descendants.extend(children)
    for child in children:
        descendants.extend(get_strict_descendants(child))
    return descendants

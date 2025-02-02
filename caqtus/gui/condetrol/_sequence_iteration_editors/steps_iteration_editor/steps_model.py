from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

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

    def child(self, row: int, column: int = 0) -> StepItem:
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

    # noqa: N802

    def __init__(self, steps: StepsConfiguration, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.set_steps(steps)
        self._read_only = True
        self.undo_stack = QUndoStack(self)

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
        self.clear()
        items = [StepItem.construct(step) for step in steps.steps]
        root = self.invisibleRootItem()
        for item in items:
            root.appendRow(item)
        self.endResetModel()

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if self._read_only:
            return False
        return super().setData(index, value, role)

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

        new_items = [StepItem.construct(step) for step in steps]

        parent_item = (
            self.itemFromIndex(parent) if parent.isValid() else self.invisibleRootItem()
        )
        if not (parent_item.flags() & Qt.ItemFlag.ItemIsDropEnabled):
            return False
        if row == -1:
            row = parent_item.rowCount()
        parent_item.insertRows(row, new_items)
        return True

    def insert_above(self, step: Step, index: QModelIndex):
        if self._read_only:
            return
        if not index.isValid():
            return
        else:
            parent = index.parent()
            self.insert_step(step, index.row(), parent)

    def insert_step(self, step: Step, row: int, parent: QModelIndex) -> bool:
        if self._read_only:
            return False
        parent_item = (
            self.itemFromIndex(parent) if parent.isValid() else self.invisibleRootItem()
        )
        new_item = StepItem.construct(step)
        parent_item.insertRows(row, [new_item])
        return True

    def append_step(self, step: Step) -> bool:
        if self._read_only:
            return False
        root = self.invisibleRootItem()
        new_item = StepItem.construct(step)
        root.appendRow(new_item)
        return True

    def removeRow(self, row, parent=DEFAULT_INDEX) -> bool:
        if self._read_only:
            return False
        index = self.index(row, 0, parent)
        item = self.itemFromIndex(index)
        self.undo_stack.push(
            self.RemoveRowCommand(self, item.get_step(), into_flat_index(index))
        )
        return True

    def into_index(self, flat_index: FlatIndex) -> QModelIndex:
        index = QModelIndex()
        for row in flat_index.rows:
            index = self.index(row, 0, index)
        return index

    @attrs.define(slots=False)
    class RemoveRowCommand(QUndoCommand):
        model: StepsModel
        step: Step
        index: FlatIndex

        def __attrs_post_init__(self):
            super().__init__(f"remove {self.step}")

        def redo(self):
            index = self.model.into_index(self.index)
            QStandardItemModel.removeRow(self.model, index.row(), index.parent())

        def undo(self):
            parent = self.model.into_index(self.index.parent())
            row = self.index.row()
            result = self.model.insert_step(self.step, row, parent)
            assert result


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


def into_flat_index(index: QModelIndex) -> FlatIndex:
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

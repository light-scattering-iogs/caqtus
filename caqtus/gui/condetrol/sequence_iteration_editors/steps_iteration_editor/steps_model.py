from __future__ import annotations

from typing import Optional

import attrs
from PySide6.QtCore import (
    QModelIndex,
    Qt,
    QObject,
)
from PySide6.QtGui import QStandardItem, QStandardItemModel, QPalette

from caqtus.types.expression import Expression
from caqtus.types.iteration import (
    StepsConfiguration,
    Step,
    ExecuteShot,
    VariableDeclaration,
    LinspaceLoop,
)
from caqtus.types.variable_name import DottedVariableName

NAME_COLOR = "#AA4926"
VALUE_COLOR = "#6897BB"
HIGHLIGHT_COLOR = "#cc7832"


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
        match step:
            case ExecuteShot():
                item.setData(ExecuteShotData(), Qt.ItemDataRole.UserRole + 1)
            case VariableDeclaration(variable=variable, value=value):
                item.setData(
                    VariableDeclarationData(variable=variable, value=value),
                    Qt.ItemDataRole.UserRole + 1,
                )
            case LinspaceLoop(
                variable=variable, start=start, stop=stop, num=num, sub_steps=sub_steps
            ):
                children = [cls.construct(sub_step) for sub_step in sub_steps]
                item.setData(
                    LinspaceLoopData(
                        variable=variable, start=start, stop=stop, num=num
                    ),
                    Qt.ItemDataRole.UserRole + 1,
                )
                item.appendRows(children)
            case _:
                raise NotImplementedError(f"Step {step} not supported")

        return item

    def data(self, role: Qt.ItemDataRole.DisplayRole = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            step_data = self.data(Qt.ItemDataRole.UserRole + 1)
            assert isinstance(step_data, StepData)
            return step_data.display_data()
        return super().data(role)

    def get_step(self) -> Step:
        data = self.data(role=Qt.ItemDataRole.UserRole + 1)
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
            case _:
                raise NotImplementedError(f"Step {data} not supported")


class StepsModel(QStandardItemModel):
    def __init__(self, steps: StepsConfiguration, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.set_steps(steps)
        self._read_only = True

    def set_read_only(self, read_only: bool):
        self._read_only = read_only

    def get_steps(self) -> StepsConfiguration:
        root = self.invisibleRootItem()
        items = [root.child(i) for i in range(root.rowCount())]
        assert all(isinstance(item, StepItem) for item in items)
        steps = [item.get_step() for item in items]
        return StepsConfiguration(steps=steps)

    def set_steps(self, steps: StepsConfiguration):
        self.beginResetModel()
        self.clear()
        items = [StepItem.construct(step) for step in steps.steps]
        root = self.invisibleRootItem()
        root.appendRows(items)
        self.endResetModel()

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if self._read_only:
            return False
        if not index.isValid():
            return False
        if role == Qt.ItemDataRole.EditRole:
            step = index.internalPointer().step
            for attribute, new_value in value.items():
                setattr(step, attribute, new_value)
            self.dataChanged.emit(index, index)
            return True
        else:
            return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)

        if self._read_only:
            flags &= ~Qt.ItemFlag.ItemIsEditable
            flags &= ~Qt.ItemFlag.ItemIsDropEnabled
        return flags

    # def supportedDropActions(self) -> Qt.DropAction:
    #     return Qt.DropAction.MoveAction
    #
    # def mimeTypes(self) -> list[str]:
    #     return ["text/plain"]
    #
    # def mimeData(self, indexes: Iterable[QModelIndex]) -> QMimeData:
    #     data = [self.data(index, Qt.ItemDataRole.EditRole) for index in indexes]
    #     serialized = serialization.to_json(data)
    #     mime_data = QMimeData()
    #     mime_data.setText(serialized)
    #     return mime_data
    #
    # def canDropMimeData(self, data, action, row: int, column: int, parent: QModelIndex):
    #     can_drop = super().canDropMimeData(data, action, row, column, parent)
    #     if can_drop and row == -1:
    #         if parent.isValid():
    #             parent_item: StepsItem = parent.internalPointer()
    #             return isinstance(parent_item.step, ContainsSubSteps)
    #     return can_drop
    #
    # def dropMimeData(
    #     self,
    #     data: QMimeData,
    #     action: Qt.DropAction,
    #     row: int,
    #     column: int,
    #     parent: QModelIndex,
    # ) -> bool:
    #     if self._read_only:
    #         return False
    #     json_string = data.text()
    #     try:
    #         steps = serialization.from_json(json_string, list[Step])
    #     except ValueError:
    #         return False
    #
    #     new_items = [StepsItem.construct(step) for step in steps]
    #     if row == -1:
    #         if not parent.isValid():
    #             return False
    #         parent_item: StepsItem = parent.internalPointer()
    #         if not isinstance(parent_item.step, ContainsSubSteps):
    #             return False
    #         self.beginInsertRows(
    #             parent,
    #             len(parent_item.children),
    #             len(parent_item.children) + len(new_items) - 1,
    #         )
    #         parent_item.insert(len(parent_item.children), new_items)
    #         self.endInsertRows()
    #         return True
    #
    #     if not parent.isValid():
    #         self.beginInsertRows(parent, row, row + len(new_items) - 1)
    #         self._steps[row:row] = new_items
    #         self.endInsertRows()
    #         return True
    #     else:
    #         parent_item: StepsItem = parent.internalPointer()
    #         self.beginInsertRows(parent, row, row + len(new_items) - 1)
    #         parent_item.insert(row, new_items)
    #         self.endInsertRows()
    #         return True

    # def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
    #     if self._read_only:
    #         return False
    #     if not parent.isValid():
    #         self.beginRemoveRows(parent, row, row)
    #         del self._steps[row]
    #         self.endRemoveRows()
    #     else:
    #         self.beginRemoveRows(parent, row, row)
    #         parent_item: StepsItem = parent.internalPointer()
    #         parent_item.remove_child(row)
    #         self.endRemoveRows()
    #     return True
    #
    # def removeRows(
    #     self, row: int, count: int, parent: QModelIndex = QModelIndex()
    # ) -> bool:
    #     if self._read_only:
    #         return False
    #     self.beginRemoveRows(parent, row, row + count - 1)
    #     if not parent.isValid():
    #         del self._steps[row : row + count]
    #     else:
    #         parent_item: StepsItem = parent.internalPointer()
    #         for _ in range(count):
    #             parent_item.remove_child(row)
    #     self.endRemoveRows()
    #     return True
    #
    # def insert_above(self, step: Step, index: QModelIndex):
    #     if self._read_only:
    #         return
    #     if not index.isValid():
    #         return
    #     else:
    #         parent = index.parent()
    #         new_item = StepsItem.construct(step)
    #         self.beginInsertRows(parent, index.row(), index.row())
    #         if not parent.isValid():
    #             self._steps.insert(index.row(), new_item)
    #         else:
    #             parent_item: StepsItem = parent.internalPointer()
    #             parent_item.insert(index.row(), [new_item])
    #         self.endInsertRows()

"""This module provides a model to interact with a tree of sequence steps.

It is meant to provide data for a view within the Qt model/view architecture. This model is used to show and interact
with the steps that a sequence execute.
"""
from __future__ import annotations

import functools
from abc import ABCMeta
from typing import Iterable, Optional

from PyQt6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
    QMimeData,
    QByteArray,
    QObject,
)
from anytree import NodeMixin

from core.session.sequence.iteration_configuration import (
    StepsConfiguration,
    Step,
    ArangeLoop,
    ExecuteShot,
    VariableDeclaration,
    LinspaceLoop,
)


class QABCMeta(type(QObject), ABCMeta):
    pass


class StepsItem(NodeMixin):
    def __init__(
        self,
        step: Step,
        parent: Optional[StepsItem] = None,
        children: Iterable[StepsItem] = tuple(),
    ):
        super().__init__()
        self.step = step
        self.parent = parent
        self.children = children

    @functools.singledispatchmethod
    @classmethod
    def construct(cls, step: Step) -> StepsItem:
        raise NotImplementedError

    @construct.register
    @classmethod
    def _(cls, step: ExecuteShot) -> StepsItem:
        return cls(step)

    @construct.register
    @classmethod
    def _(cls, step: ArangeLoop) -> StepsItem:
        return cls(step, children=[cls.construct(step) for step in step.sub_steps])

    @construct.register
    @classmethod
    def _(cls, step: VariableDeclaration) -> StepsItem:
        return cls(step)

    @construct.register
    @classmethod
    def _(cls, step: LinspaceLoop) -> StepsItem:
        return cls(step, children=[cls.construct(step) for step in step.sub_steps])


class StepsModel(QAbstractItemModel):
    def __init__(self, steps: StepsConfiguration, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._steps = [StepsItem.construct(step) for step in steps.steps]

    def row(self, item: StepsItem) -> int:
        if item.parent is None:
            return self._steps.index(item)
        else:
            return item.parent.children.index(item)

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            current_item = self._steps[row]
        else:
            parent_item: StepsItem = parent.internalPointer()
            if row < len(parent_item.children):
                current_item = parent_item.children[row]
            else:
                return QModelIndex()

        return self.createIndex(row, column, current_item)

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()

        child_item: StepsItem = child.internalPointer()
        if child_item.parent is None:
            return QModelIndex()
        else:
            parent_item = child_item.parent
            return self.createIndex(
                self.row(parent_item), child.column(), child_item.parent
            )

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._steps)
        else:
            parent_item: StepsItem = parent.internalPointer()
            return len(parent_item.children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                return str(index.internalPointer())

    # def setData(self, index: QModelIndex, values: dict[str], role: int = ...) -> bool:
    #     if index.isValid() and role == Qt.ItemDataRole.EditRole:
    #         node: Step = index.internalPointer()
    #         for attr, value in values.items():
    #             setattr(node, attr, value)
    #         return True
    #     else:
    #         return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.isValid() and index.column() == 0:
            flags = (
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
                | Qt.ItemFlag.ItemIsEnabled
            )
        else:
            flags = Qt.ItemFlag.NoItemFlags
        return flags

    # # noinspection PyTypeChecker
    # def supportedDropActions(self) -> Qt.DropAction:
    #     return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction
    #
    # def mimeTypes(self) -> list[str]:
    #     return ["application/x-sequence_steps"]
    #
    # def mimeData(self, indexes: Iterable[QModelIndex]) -> QMimeData:
    #     data = [self.data(index, Qt.ItemDataRole.DisplayRole) for index in indexes]
    #     serialized = YAMLSerializable.dump(data).encode("utf-8")
    #     mime_data = QMimeData()
    #     mime_data.setData("application/x-sequence_steps", QByteArray(serialized))
    #     return mime_data
    #
    # def dropMimeData(
    #     self,
    #     data: QMimeData,
    #     action: Qt.DropAction,
    #     row: int,
    #     column: int,
    #     parent: QModelIndex,
    # ) -> bool:
    #     yaml_string = data.data("application/x-sequence_steps").data().decode("utf-8")
    #     steps: list[Step] = YAMLSerializable.load(yaml_string)
    #     if not parent.isValid():
    #         node = self.root
    #     else:
    #         node: Step = parent.internalPointer()
    #     if row == -1:
    #         position = len(node.children)
    #     else:
    #         position = row
    #     self.beginInsertRows(parent, position, position + len(steps) - 1)
    #     new_children = list(node.children)
    #     for step in steps[::-1]:
    #         new_children.insert(position, step)
    #     node.children = new_children
    #     self.endInsertRows()
    #     return True
    #
    # def insert_step(self, new_step: Step, index: QModelIndex):
    #     # insert at the end of all steps if clicked at invalid index
    #     if not index.isValid():
    #         position = len(self.root.children)
    #         self.beginInsertRows(QModelIndex(), position, position)
    #         self.root.children += (new_step,)
    #         self.endInsertRows()
    #     else:
    #         node: Step = index.internalPointer()
    #         # if the selected step can't have children, the new step is added below it
    #         if isinstance(node, (VariableDeclaration, ExecuteShot)):
    #             position = index.row() + 1
    #             self.beginInsertRows(QModelIndex(), position, position)
    #             new_children = list(node.parent.children)
    #             new_children.insert(position, new_step)
    #             node.parent.children = new_children
    #             self.endInsertRows()
    #         # otherwise it's added as the last child of the selected step
    #         else:
    #             position = len(node.children)
    #             self.beginInsertRows(index, position, position)
    #             new_children = list(node.children)
    #             new_children.insert(position, new_step)
    #             node.children = new_children
    #             self.endInsertRows()
    #
    # def removeRow(self, row: int, parent: QModelIndex = ...) -> bool:
    #     self.beginRemoveRows(parent, row, row)
    #     if not parent.isValid():
    #         parent = self.root
    #     else:
    #         parent: Step = parent.internalPointer()
    #     new_children = list(parent.children)
    #     new_children.pop(row)
    #     parent.children = new_children
    #     self.endRemoveRows()
    #     return True
    #
    # def removeRows(self, row: int, count: int, parent: QModelIndex = ...) -> bool:
    #     self.beginRemoveRows(parent, row, row + count - 1)
    #     if not parent.isValid():
    #         parent = self.root
    #     else:
    #         parent: Step = parent.internalPointer()
    #     new_children = list(parent.children)
    #     for _ in range(count):
    #         new_children.pop(row)
    #     parent.children = new_children
    #     self.endRemoveRows()
    #     return True
    #
    # def set_steps(self, steps: list[Step]):
    #     steps = list(steps)
    #     if not isinstance(steps, list):
    #         raise TypeError(
    #             f"Expected a list of {Step.__name__} instances, got {type(steps)}"
    #         )
    #     if not all(isinstance(step, Step) for step in steps):
    #         raise TypeError(f"Expected a list of {Step.__name__} instances")
    #     self.beginResetModel()
    #     self.root.children = steps
    #     self.endResetModel()

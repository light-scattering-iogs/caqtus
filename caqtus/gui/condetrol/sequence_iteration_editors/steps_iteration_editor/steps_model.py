from __future__ import annotations

import copy
import functools
from typing import Iterable, Optional

from PySide6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
    QMimeData,
    QObject,
)
from anytree import NodeMixin

from caqtus.types.iteration import (
    StepsConfiguration,
    Step,
    ArangeLoop,
    ExecuteShot,
    VariableDeclaration,
    LinspaceLoop,
    ContainsSubSteps,
)
from caqtus.utils import serialization


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

    def remove_child(self, row: int):
        if isinstance(self.step, ContainsSubSteps):
            self.children[row].parent = None
            del self.step.sub_steps[row]
        else:
            raise TypeError(f"Cannot remove child from {self.step}")

    def insert(self, row: int, items: list[StepsItem]):
        if isinstance(self.step, ContainsSubSteps):
            children = list(self.children)
            children[row:row] = items
            self.children = children
            self.step.sub_steps[row:row] = [item.step for item in items]
        else:
            raise TypeError(f"Cannot insert child into {self.step}")

    @functools.singledispatchmethod
    @classmethod
    def construct(cls, step: Step) -> "StepsItem":
        raise NotImplementedError

    @construct.register
    @classmethod
    def _(cls, step: ExecuteShot):
        return cls(step)

    @construct.register
    @classmethod
    def _(cls, step: ArangeLoop):
        return cls(step, children=[cls.construct(step) for step in step.sub_steps])

    @construct.register
    @classmethod
    def _(cls, step: VariableDeclaration):
        return cls(step)

    @construct.register
    @classmethod
    def _(cls, step: LinspaceLoop):
        return cls(step, children=[cls.construct(step) for step in step.sub_steps])


class StepsModel(QAbstractItemModel):
    def __init__(self, steps: StepsConfiguration, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._steps = [StepsItem.construct(step) for step in steps.steps]
        self._read_only = True

    def set_read_only(self, read_only: bool):
        self._read_only = read_only

    def get_steps(self) -> StepsConfiguration:
        return StepsConfiguration(
            steps=[copy.deepcopy(item.step) for item in self._steps],
        )

    def set_steps(self, steps: StepsConfiguration):
        self.beginResetModel()
        self._steps = [StepsItem.construct(step) for step in steps.steps]
        self.endResetModel()

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
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return index.internalPointer().step

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
        flags = (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
            | Qt.ItemFlag.ItemIsEnabled
        )
        if index.isValid():
            step = index.internalPointer().step
            if not isinstance(step, ExecuteShot):
                flags |= Qt.ItemFlag.ItemIsEditable

        if self._read_only:
            flags &= ~Qt.ItemFlag.ItemIsEditable
            flags &= ~Qt.ItemFlag.ItemIsDropEnabled
        return flags

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return ["text/plain"]

    def mimeData(self, indexes: Iterable[QModelIndex]) -> QMimeData:
        data = [self.data(index, Qt.ItemDataRole.EditRole) for index in indexes]
        serialized = serialization.to_json(data)
        mime_data = QMimeData()
        mime_data.setText(serialized)
        return mime_data

    def canDropMimeData(self, data, action, row: int, column: int, parent: QModelIndex):
        can_drop = super().canDropMimeData(data, action, row, column, parent)
        if can_drop and row == -1:
            if parent.isValid():
                parent_item: StepsItem = parent.internalPointer()
                return isinstance(parent_item.step, ContainsSubSteps)
        return can_drop

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if self._read_only:
            return False
        json_string = data.text()
        try:
            steps = serialization.from_json(json_string, list[Step])
        except ValueError:
            return False

        new_items = [StepsItem.construct(step) for step in steps]
        if row == -1:
            if not parent.isValid():
                return False
            parent_item: StepsItem = parent.internalPointer()
            if not isinstance(parent_item.step, ContainsSubSteps):
                return False
            self.beginInsertRows(
                parent,
                len(parent_item.children),
                len(parent_item.children) + len(new_items) - 1,
            )
            parent_item.insert(len(parent_item.children), new_items)
            self.endInsertRows()
            return True

        if not parent.isValid():
            self.beginInsertRows(parent, row, row + len(new_items) - 1)
            self._steps[row:row] = new_items
            self.endInsertRows()
            return True
        else:
            parent_item: StepsItem = parent.internalPointer()
            self.beginInsertRows(parent, row, row + len(new_items) - 1)
            parent_item.insert(row, new_items)
            self.endInsertRows()
            return True

    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        if self._read_only:
            return False
        if not parent.isValid():
            self.beginRemoveRows(parent, row, row)
            del self._steps[row]
            self.endRemoveRows()
        else:
            self.beginRemoveRows(parent, row, row)
            parent_item: StepsItem = parent.internalPointer()
            parent_item.remove_child(row)
            self.endRemoveRows()
        return True

    def removeRows(
        self, row: int, count: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        if self._read_only:
            return False
        self.beginRemoveRows(parent, row, row + count - 1)
        if not parent.isValid():
            del self._steps[row : row + count]
        else:
            parent_item: StepsItem = parent.internalPointer()
            for _ in range(count):
                parent_item.remove_child(row)
        self.endRemoveRows()
        return True

    def insert_above(self, step: Step, index: QModelIndex):
        if self._read_only:
            return
        if not index.isValid():
            return
        else:
            parent = index.parent()
            new_item = StepsItem.construct(step)
            self.beginInsertRows(parent, index.row(), index.row())
            if not parent.isValid():
                self._steps.insert(index.row(), new_item)
            else:
                parent_item: StepsItem = parent.internalPointer()
                parent_item.insert(index.row(), [new_item])
            self.endInsertRows()

from typing import Optional

from PySide6.QtCore import QObject, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

from caqtus.session import ExperimentSessionMaker, PureSequencePath
from caqtus.session._return_or_raise import unwrap
from caqtus.session.path_hierarchy import PathNotFoundError
from caqtus.session.sequence_collection import PathIsSequenceError

FULL_PATH = Qt.UserRole + 1
HAS_FETCHED_CHILDREN = Qt.UserRole + 2
IS_SEQUENCE = Qt.UserRole + 3


class AsyncPathHierarchyModel(QAbstractItemModel):
    def __init__(
        self, session_maker: ExperimentSessionMaker, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.session_maker = session_maker

        self.tree = QStandardItemModel(self)
        self.tree.invisibleRootItem().setData(False, HAS_FETCHED_CHILDREN)
        self.tree.invisibleRootItem().setData(PureSequencePath.root(), FULL_PATH)
        self.tree.invisibleRootItem().setData(False, IS_SEQUENCE)

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_item = (
            parent.internalPointer()
            if parent.isValid()
            else self.tree.invisibleRootItem()
        )
        child_item = parent_item.child(row)
        return (
            self.createIndex(row, column, child_item) if child_item else QModelIndex()
        )

    def parent(self, index=QModelIndex()):
        if not index.isValid():
            return QModelIndex()
        child_item = index.internalPointer()
        parent_item = child_item.parent()
        if parent_item is None:
            return QModelIndex()
        return (
            self.createIndex(parent_item.row(), index.column(), parent_item)
            if parent_item is not self.tree.invisibleRootItem()
            else QModelIndex()
        )

    def _get_item(self, index) -> QStandardItem:
        result = (
            index.internalPointer()
            if index.isValid()
            else self.tree.invisibleRootItem()
        )
        assert isinstance(result, QStandardItem)
        return result

    def rowCount(self, parent=QModelIndex()):
        parent_item = self._get_item(parent)
        if parent_item.data(IS_SEQUENCE):
            return 0
        if parent_item.data(HAS_FETCHED_CHILDREN):
            return parent_item.rowCount()
        else:
            return 0

    def hasChildren(self, parent=QModelIndex()) -> bool:
        parent_item = self._get_item(parent)
        if parent_item.data(IS_SEQUENCE):
            return False
        if parent_item.data(HAS_FETCHED_CHILDREN):
            return parent_item.rowCount() > 0
        else:
            return True

    def canFetchMore(self, parent) -> bool:
        parent_item = self._get_item(parent)
        if parent_item.data(IS_SEQUENCE):
            return False
        return not parent_item.data(HAS_FETCHED_CHILDREN)

    def fetchMore(self, parent):
        parent_item = self._get_item(parent)
        if parent_item.data(IS_SEQUENCE):
            return
        if parent_item.data(HAS_FETCHED_CHILDREN):
            return

        parent_path = parent_item.data(FULL_PATH)
        with self.session_maker() as session:
            children_result = session.paths.get_children(parent_path)
        try:
            children = unwrap(children_result)
        except PathIsSequenceError:
            parent_item.setData(True, IS_SEQUENCE)
        except PathNotFoundError:
            pass
        else:
            self.beginInsertRows(parent, 0, len(children) - 1)
            for child_path in children:
                child_item = QStandardItem()
                child_item.setData(child_path.name, Qt.DisplayRole)
                child_item.setData(child_path, FULL_PATH)
                child_item.setData(False, HAS_FETCHED_CHILDREN)
                child_item.setData(False, IS_SEQUENCE)
                parent_item.appendRow(child_item)
                parent_item.setData(True, HAS_FETCHED_CHILDREN)
            self.endInsertRows()

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self._get_item(index)
        return item.data(role)

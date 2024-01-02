from __future__ import annotations

import datetime
import threading
from typing import Optional

from PyQt6.QtCore import (
    QAbstractItemModel,
    QThread,
    QModelIndex,
    Qt,
    QTimer,
    pyqtSignal,
    QDateTime,
)
from anytree import NodeMixin

from core.session import PureSequencePath, ExperimentSessionMaker
from core.session.path_hierarchy import PathNotFoundError
from core.session.result import unwrap, Failure
from core.session.sequence_collection import PathIsSequenceError


class PathHierarchyItem(NodeMixin):
    def __init__(
        self,
        path: PureSequencePath,
        parent: Optional[PathHierarchyItem],
        creation_date: Optional[datetime.datetime],
    ):
        super().__init__()
        self.hierarchy_path = path
        self.parent = parent
        self.children = []
        self.creation_date = creation_date

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0


class PathHierarchyModel(QAbstractItemModel):
    def __init__(self, session_maker: ExperimentSessionMaker, parent=None):
        super().__init__(parent)
        self._tree_structure_lock = threading.Lock()
        self._root = PathHierarchyItem(PureSequencePath.root(), None, None)
        self._session_maker = session_maker
        self._thread = self.TreeUpdateThread(self, self._root, self._session_maker)
        self._thread.item_structure_changed.connect(self.process_structure_change)
        self._thread.creation_date_changed.connect(
            lambda index: self.dataChanged.emit(index, index)
        )

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._thread.quit()
        self._thread.wait()

    def get_path(self, index: QModelIndex) -> PureSequencePath:
        if not index.isValid():
            return self._root.hierarchy_path
        item: PathHierarchyItem = index.internalPointer()
        return item.hierarchy_path

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent_item = self._root
        else:
            parent_item = parent.internalPointer()

        if row >= len(parent_item.children):
            return QModelIndex()
        child_item = parent_item.children[row]
        return self.createIndex(row, column, child_item)

    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()

        child_item: PathHierarchyItem = index.internalPointer()
        parent_item = child_item.parent
        if not parent_item:
            return QModelIndex()
        if parent_item is self._root:
            return QModelIndex()
        return self.createIndex(parent_item.row(), index.column(), parent_item)

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return len(self._root.children)
        item = parent.internalPointer()
        return len(item.children)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        item: PathHierarchyItem = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return item.hierarchy_path.name
            elif index.column() == 1:
                return QDateTime(item.creation_date)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return "Name"
                elif section == 1:
                    return "Date created"
            else:
                return section
        return None

    def process_structure_change(self, parent: QModelIndex):
        if not parent.isValid():
            parent_item = self._root
        else:
            parent_item: PathHierarchyItem = parent.internalPointer()

        with self._tree_structure_lock, self._session_maker() as session:
            children_query = session.paths.get_children(parent_item.hierarchy_path)
            if isinstance(children_query, Failure):
                self._thread.start()
                return
            else:
                fetched_child_paths = children_query.unwrap()
            present_paths = {child.hierarchy_path for child in parent_item.children}
            for row in range(len(parent_item.children) - 1, -1, -1):
                child = parent_item.children[row]
                if child.hierarchy_path not in fetched_child_paths:
                    self.beginRemoveRows(parent, row, row)
                    child.parent = None
                    self.endRemoveRows()
            new_paths = fetched_child_paths - present_paths
            new_children = [
                PathHierarchyItem(
                    path,
                    None,
                    unwrap(session.paths.get_path_creation_date(path)),
                )
                for path in new_paths
            ]
            self.beginInsertRows(
                parent,
                len(parent_item.children),
                len(parent_item.children) + len(new_children) - 1,
            )
            for child in new_children:
                child.parent = parent_item
            self.endInsertRows()
        self._thread.start()

    class TreeUpdateThread(QThread):
        item_structure_changed = pyqtSignal(QModelIndex)
        creation_date_changed = pyqtSignal(QModelIndex)

        def __init__(
            self,
            parent: PathHierarchyModel,
            root: PathHierarchyItem,
            session_maker: ExperimentSessionMaker,
        ):
            super().__init__(parent)
            self._parent = parent
            self.lock = parent._tree_structure_lock
            self.root = root
            self.session = session_maker()

        def run(self):
            timer = QTimer()

            def update():
                with self.lock, self.session:
                    try:
                        self.check_item_change(QModelIndex())
                    except PathNotFoundError:
                        pass
                    except FoundChange as e:
                        self.item_structure_changed.emit(e.index)

            timer.timeout.connect(update)  # type: ignore
            timer.start(0)
            self.exec()
            timer.stop()

        def check_item_change(self, index: QModelIndex) -> None:
            self.check_creation_date_changed(index)
            if not index.isValid():
                path_item = self.root
            else:
                path_item = index.internalPointer()
            path = path_item.hierarchy_path
            try:
                fetched_child_paths = unwrap(self.session.paths.get_children(path))
            except PathIsSequenceError:
                return
            present_child_paths = {child.hierarchy_path for child in path_item.children}
            if fetched_child_paths != present_child_paths:
                raise FoundChange(index)
            else:
                for child in path_item.children:
                    child_index = self._parent.index(child.row(), 0, index)
                    self.check_item_change(child_index)

        def check_creation_date_changed(self, index: QModelIndex) -> bool:
            if not index.isValid():
                return False
            else:
                path_item = index.internalPointer()
                path = path_item.hierarchy_path
                creation_date = unwrap(self.session.paths.get_path_creation_date(path))
                if creation_date != path_item.creation_date:
                    path_item.creation_date = creation_date
                    self.creation_date_changed.emit(index.sibling(index.row(), 1))


class FoundChange(Exception):
    def __init__(self, index: QModelIndex):
        self.index = index

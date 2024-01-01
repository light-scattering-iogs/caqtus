from __future__ import annotations

import threading
from typing import Optional

from PyQt6.QtCore import (
    QAbstractItemModel,
    QThread,
    QModelIndex,
    Qt,
    QTimer,
    pyqtSignal,
)
from anytree import NodeMixin

from core.session import PureSequencePath, ExperimentSessionMaker
from core.session.result import Failure, Success, unwrap


class PathHierarchyItem(NodeMixin):
    def __init__(self, path: PureSequencePath, parent: Optional[PathHierarchyItem]):
        super().__init__()
        self.hierarchy_path = path
        self.parent = parent
        self.children = []
        self.children_in_session: set[PureSequencePath] = set()

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0


class PathHierarchyModel(QAbstractItemModel):
    def __init__(self, session_maker: ExperimentSessionMaker, parent=None):
        super().__init__(parent)
        self._tree_structure_lock = threading.Lock()
        self._root = PathHierarchyItem(PureSequencePath.root(), None)
        self._session_maker = session_maker
        self._thread = self.TreeUpdateThread(self, self._root, self._session_maker)
        self._thread.item_content_changed.connect(self.process_item_change)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._thread.quit()
        self._thread.wait()

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            return self.createIndex(0, column, self._root)
        else:
            parent_item = parent.internalPointer()

        if row >= len(parent_item.children):
            return QModelIndex()
        child_item = parent_item.children[row]
        return self.createIndex(row, column, child_item)

    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()
        parent_item = child_item.parent
        if not parent_item:
            return QModelIndex()
        return self.createIndex(parent_item.row(), index.column(), parent_item)

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            return 1
        item = parent.internalPointer()
        return len(item.children)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        item = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            return str(item.hierarchy_path)
        return None

    def process_item_change(self, parent: QModelIndex):
        if not parent.isValid():
            return
        parent_item = parent.internalPointer()

        with self._tree_structure_lock, self._session_maker() as session:
            self.beginRemoveRows(parent, 0, len(parent_item.children))
            parent_item.children = []
            self.endRemoveRows()
            fetched_child_paths = unwrap(
                session.sequence_hierarchy.get_children(parent_item.hierarchy_path)
            )
            parent_item.children_in_session = set(fetched_child_paths)
            self.beginInsertRows(parent, 0, len(fetched_child_paths))
            parent_item.children = [
                PathHierarchyItem(path, None) for path in fetched_child_paths
            ]
            self.endInsertRows()

    class TreeUpdateThread(QThread):
        item_content_changed = pyqtSignal(QModelIndex)

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
            self.session_maker = session_maker

        def run(self):
            timer = QTimer()

            def update():
                with self.lock:
                    self.update_tree_data(self._parent.index(0, 0, QModelIndex()))

            timer.timeout.connect(update)  # type: ignore
            timer.start(0)
            self.exec()

        def update_tree_data(self, index: QModelIndex):
            path_item = index.internalPointer()
            path = path_item.hierarchy_path
            present_child_paths = {child.hierarchy_path for child in path_item.children}
            with self.session_maker() as session:
                result = session.sequence_hierarchy.get_children(path)
            match result:
                case Failure():
                    # The path was changed in the session by another application,
                    # so we return ASAP to retry walking the tree and find the
                    # path closest to the root that changed.
                    return
                case Success(fetched_child_paths):
                    if fetched_child_paths != present_child_paths:
                        self.item_content_changed.emit(index)  # type: ignore
                        return
                    else:
                        for child in path_item.children:
                            child_index = index.model().index(child.row(), 0, index)
                            self.update_tree_data(child_index)

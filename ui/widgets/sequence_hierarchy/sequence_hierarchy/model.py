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
from core.session.result import unwrap, Success, Failure


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
        self.children_in_session: set[PureSequencePath] = set()
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
                    return "Sequence"
                elif section == 1:
                    return "Created"
            else:
                return section
        return None

    def process_item_change(self, parent: QModelIndex):
        if not parent.isValid():
            parent_item = self._root
        else:
            parent_item: PathHierarchyItem = parent.internalPointer()

        with self._tree_structure_lock, self._session_maker() as session:
            self.beginRemoveRows(parent, 0, len(parent_item.children) - 1)
            parent_item.children = []
            self.endRemoveRows()
            fetched_child_paths = unwrap(
                session.sequence_hierarchy.get_children(parent_item.hierarchy_path)
            )
            parent_item.children_in_session = set(fetched_child_paths)
            new_children = [
                PathHierarchyItem(
                    path,
                    None,
                    unwrap(session.sequence_hierarchy.get_path_creation_date(path)),
                )
                for path in fetched_child_paths
            ]
            self.beginInsertRows(parent, 0, len(fetched_child_paths) - 1)
            parent_item.children = new_children
            self.endInsertRows()
        self._thread.start()

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
            self.session = session_maker()

        def run(self):
            timer = QTimer()

            def update():
                with self.lock, self.session:
                    self.check_item_change(QModelIndex())

            timer.timeout.connect(update)  # type: ignore
            timer.start(0)
            self.exec()

        def check_item_change(self, index: QModelIndex) -> bool:
            if not index.isValid():
                path_item = self.root
            else:
                path_item = index.internalPointer()
            path = path_item.hierarchy_path
            match self.session.sequence_hierarchy.get_children(path):
                case Failure():
                    return True
                case Success(fetched_child_paths):
                    present_child_paths = {
                        child.hierarchy_path for child in path_item.children
                    }
                    if fetched_child_paths != present_child_paths:
                        # We don't want to emit new signals until the changes are
                        # processed, so we emit the signal and quit the thread.
                        # The thread will be restarted by the parent when the changes
                        # are processed.
                        self.item_content_changed.emit(index)  # type: ignore
                        self.quit()
                        return True
                    else:
                        for child in path_item.children:
                            child_index = self._parent.index(child.row(), 0, index)
                            if self.check_item_change(child_index):
                                return True
                        return False

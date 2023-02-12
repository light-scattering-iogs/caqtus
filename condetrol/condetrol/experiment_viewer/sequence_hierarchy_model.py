import time

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt
from anytree import NodeMixin
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from sequence.runtime import SequencePath
from sequence.runtime.model import SequenceModel


class SequenceHierarchyModel(QAbstractItemModel):
    """Tree model for sequence hierarchy.

    This model stores an in-memory representation of the database sequence structure.
    """

    def __init__(self, session_maker: sessionmaker):
        self._session_maker = session_maker

        self._root = SequenceHierarchyItem(
            SequencePath.root(),
            children=_build_highest_level(
                SequencePath.root(), self._get_sequence_infos(SequencePath.root())
            ),
            row=0,
            is_sequence=False,
        )

        super().__init__()

    def index(self, row: int, column: int, parent: QModelIndex = ...) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        elif not parent.isValid():
            return self.createIndex(row, column, self._root.children[row])
        else:
            parent: SequenceHierarchyItem = parent.internalPointer()
            if row < len(parent.children):
                return self.createIndex(row, column, parent.children[row])
            else:
                return QModelIndex()

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()

        child: SequenceHierarchyItem = child.internalPointer()
        if child.is_root:
            return QModelIndex()
        else:
            return self.createIndex(child.parent.row, 0, child.parent)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        if not parent.isValid():
            return len(self._root.children)
        else:
            return len(parent.internalPointer().children)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = ...):
        if not index.isValid():
            return

        if role == Qt.ItemDataRole.DisplayRole:
            return index.internalPointer().sequence_path.name

    def hasChildren(self, parent: QModelIndex = ...) -> bool:
        if not parent.isValid():
            return True
        else:
            return parent.internalPointer().is_folder()

    def canFetchMore(self, parent: QModelIndex) -> bool:
        if not parent.isValid():
            return False
        else:
            parent_item: SequenceHierarchyItem = parent.internalPointer()
            return parent_item.is_folder() and len(parent_item.children) == 0

    def fetchMore(self, parent: QModelIndex) -> None:
        if not parent.isValid():
            return

        parent_item: SequenceHierarchyItem = parent.internalPointer()

        if parent_item.is_sequence:
            return

        print(parent_item)

        children = _build_highest_level(
            parent_item.sequence_path,
            self._get_sequence_infos(path_prefix=parent_item.sequence_path),
        )

        self.beginInsertRows(parent, 0, len(children) - 1)
        parent_item.children = children
        self.endInsertRows()

    def _get_sequence_infos(self, path_prefix: SequencePath) -> list[dict]:
        query = select(SequenceModel.path, SequenceModel.state).filter(
            SequenceModel.path.startswith(str(path_prefix))
        )
        with self._session_maker.begin() as session:
            result = session.execute(query)
        return [{"path": path, "state": state} for path, state in result]


class SequenceHierarchyItem(NodeMixin):
    """Item in the sequence hierarchy model.

    This class represents a single item in the sequence hierarchy model.
    """

    def __init__(
        self,
        path: SequencePath,
        is_sequence: bool,
        row: int,
        parent=None,
        children=None,
    ):
        super().__init__()
        self.sequence_path = path
        self.parent = parent
        self.is_sequence = is_sequence
        self.row = row
        if children:
            self.children = children

    def __repr__(self):
        return f"{self.__class__.__name__}({self.sequence_path})"

    def is_folder(self):
        return not self.is_sequence


def _build_highest_level(
    parent: SequencePath, sequence_infos: list[dict]
) -> list[SequenceHierarchyItem]:
    """Build the root of the sequence hierarchy model

    This function builds the higher level hierarchy of the sequence hierarchy model.
    """
    top_level_names = set()
    top_level_nodes = []
    for sequence_info in sequence_infos:
        sequence_path = SequencePath(sequence_info["path"])
        if sequence_path.has_ancestor(parent):
            sub_path = sequence_path.get_ancestors(strict=False)[parent.depth + 1]
            is_sub_path_sequence = str(sub_path) == str(sequence_path)
            if sub_path.name not in top_level_names:
                top_level_nodes.append(
                    SequenceHierarchyItem(
                        sub_path,
                        row=len(top_level_names),
                        is_sequence=is_sub_path_sequence,
                    )
                )
            top_level_names.add(sub_path.name)
    return top_level_nodes

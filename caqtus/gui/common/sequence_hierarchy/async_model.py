from __future__ import annotations

import asyncio
import datetime
from typing import Optional, TypeGuard

import attrs
from PySide6.QtCore import QObject, QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

from caqtus.session import ExperimentSessionMaker, PureSequencePath, ExperimentSession
from caqtus.session._return_or_raise import unwrap
from caqtus.session.path_hierarchy import PathNotFoundError
from caqtus.session.sequence_collection import PathIsSequenceError, SequenceStats

NODE_DATA_ROLE = Qt.UserRole + 1


def get_item_data(item: QStandardItem) -> Node:
    data = item.data(NODE_DATA_ROLE)
    assert is_node(data)
    return data


@attrs.define
class FolderNode:
    path: PureSequencePath
    has_fetched_children: bool
    creation_date: datetime.datetime


@attrs.define
class SequenceNode:
    path: PureSequencePath
    stats: SequenceStats
    creation_date: datetime.datetime


Node = FolderNode | SequenceNode


def is_node(value) -> TypeGuard[Node]:
    return isinstance(value, (FolderNode, SequenceNode))


class AsyncPathHierarchyModel(QAbstractItemModel):
    def __init__(
        self, session_maker: ExperimentSessionMaker, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.session_maker = session_maker

        self.tree = QStandardItemModel(self)
        self.tree.invisibleRootItem().setData(
            FolderNode(
                path=PureSequencePath.root(),
                has_fetched_children=False,
                creation_date=datetime.datetime.min,
            ),
            NODE_DATA_ROLE,
        )

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
        node_data = get_item_data(parent_item)
        match node_data:
            case SequenceNode():
                return 0
            case FolderNode(has_fetched_children=True):
                return parent_item.rowCount()
            case FolderNode(has_fetched_children=False):
                return 0

    def hasChildren(self, parent=QModelIndex()) -> bool:
        parent_item = self._get_item(parent)
        node_data = get_item_data(parent_item)
        match node_data:
            case SequenceNode():
                return False
            case FolderNode(has_fetched_children=True):
                return parent_item.rowCount() > 0
            case FolderNode(has_fetched_children=False):
                return True

    def canFetchMore(self, parent) -> bool:
        parent_item = self._get_item(parent)
        node_data = get_item_data(parent_item)
        match node_data:
            case SequenceNode():
                return False
            case FolderNode(has_fetched_children=already_fetched):
                return not already_fetched

    def fetchMore(self, parent):
        parent_item = self._get_item(parent)
        node_data = get_item_data(parent_item)
        match node_data:
            case SequenceNode():
                return
            case FolderNode(has_fetched_children=True):
                return
            case FolderNode(path=parent_path, has_fetched_children=False):
                assert parent_item.rowCount() == 0
                with self.session_maker() as session:
                    children_result = session.paths.get_children(parent_path)
                    try:
                        children = unwrap(children_result)
                    except PathIsSequenceError:
                        stats = unwrap(session.sequences.get_stats(parent_path))
                        creation_date = unwrap(
                            session.paths.get_path_creation_date(parent_path)
                        )
                        parent_item.setData(
                            SequenceNode(
                                path=parent_path,
                                stats=stats,
                                creation_date=creation_date,
                            ),
                            NODE_DATA_ROLE,
                        )
                        return
                    except PathNotFoundError:
                        node_data.has_fetched_children = True
                        return
                    self.beginInsertRows(parent, 0, len(children) - 1)
                    for child_path in children:
                        child_item = self._build_item(child_path, session)
                        parent_item.appendRow(child_item)
                        node_data.has_fetched_children = True
                    self.endInsertRows()

    @staticmethod
    def _build_item(
        path: PureSequencePath, session: ExperimentSession
    ) -> QStandardItem:
        assert session.paths.does_path_exists(path)
        item = QStandardItem()
        item.setData(path.name, Qt.DisplayRole)
        is_sequence = unwrap(session.sequences.is_sequence(path))
        creation_date = unwrap(session.paths.get_path_creation_date(path))
        if is_sequence:
            stats = unwrap(session.sequences.get_stats(path))
            item.setData(
                SequenceNode(path=path, stats=stats, creation_date=creation_date),
                NODE_DATA_ROLE,
            )
        else:
            item.setData(
                FolderNode(
                    path=path, has_fetched_children=False, creation_date=creation_date
                ),
                NODE_DATA_ROLE,
            )
        return item

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Get the data for a specific index in the model.

        The displayed data returned for each column is as follows:
        0: Name
        A string with the name of the folder or sequence.
        1: Status
        The status of the sequence.
        It is None for folders and a SequenceStats object for sequences.
        2: Progress
        A string representing the number of completed shots and the total
        number of shots of the sequence.
        It is None for folders.
        3: Duration
        A string representing the elapsed and remaining time of the
        sequence.
        It is None for folders.
        4: Date created
        A QDateTime object representing the date and time when the
        sequence or folder was created.
        """

        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        item = self._get_item(index)
        node_data = get_item_data(item)
        if index.column() == 0:
            return node_data.path.name
        elif index.column() == 1:
            if isinstance(node_data, SequenceNode):
                return node_data.stats
            else:
                return None
        elif index.column() == 2:
            if isinstance(node_data, SequenceNode):
                return (
                    f"{node_data.stats.number_completed_shots}"
                    f"/{node_data.stats.expected_number_shots}"
                )
            else:
                return None
        elif index.column() == 3:
            return None
        elif index.column() == 4:
            return node_data.creation_date

    async def watch_session(self) -> None:
        while True:
            await self.update_from_session()
            await asyncio.sleep(50e-3)

    async def update_from_session(self) -> None:
        await self.prune()

    async def prune(self, parent: QModelIndex = QModelIndex()) -> None:
        """Removes items from the model that no longer exist in the session."""

        parent_item = self._get_item(parent)
        parent_data = get_item_data(parent_item)
        with self.session_maker() as session:
            children_result = await asyncio.to_thread(
                session.paths.get_children, parent_data.path
            )
            try:
                child_paths = unwrap(children_result)
            except PathIsSequenceError:
                stats = unwrap(session.sequences.get_stats(parent_data.path))
                creation_date = unwrap(
                    session.paths.get_path_creation_date(parent_data.path)
                )
                self.beginRemoveRows(parent, 0, parent_item.rowCount() - 1)
                parent_item.setData(
                    SequenceNode(
                        path=parent_data.path, stats=stats, creation_date=creation_date
                    ),
                    NODE_DATA_ROLE,
                )
                parent_item.removeRows(0, parent_item.rowCount())
                self.endRemoveRows()
                return
            except PathNotFoundError:
                grandparent = self.parent(parent)
                grandparent_item = self._get_item(grandparent)
                self.beginRemoveRows(grandparent, parent.row(), parent.row())
                grandparent_item.removeRow(parent.row())
                self.endRemoveRows()
                return

        # Need to remove children in reverse order to avoid invalidating rows
        for row in reversed(range(self.rowCount(parent))):
            child = self.index(row, 0, parent)
            child_item = self._get_item(child)
            child_path = get_item_data(child_item).path
            if child_path not in child_paths:
                self.beginRemoveRows(parent, row, row)
                parent_item.removeRow(row)
                self.endRemoveRows()
            else:
                await self.prune(child)

from __future__ import annotations

import abc
import asyncio
import datetime
from typing import Optional, TypeGuard

import attrs
from PySide6.QtCore import QObject, QAbstractItemModel, QModelIndex, Qt, QDateTime
from PySide6.QtGui import QStandardItemModel, QStandardItem

from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    ExperimentSession,
    AsyncExperimentSession,
)
from caqtus.session._return_or_raise import unwrap
from caqtus.session.path_hierarchy import PathNotFoundError
from caqtus.session.sequence import State
from caqtus.types.iteration import is_unknown
from caqtus.session.sequence_collection import (
    PathIsSequenceError,
    SequenceStats,
    PathIsNotSequenceError,
)

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
class SequenceNode(abc.ABC):
    path: PureSequencePath
    stats: SequenceStats
    creation_date: datetime.datetime
    last_query_time: datetime.datetime


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
            self.createIndex(parent_item.row(), 0, parent_item)
            if parent_item is not self.tree.invisibleRootItem()
            else QModelIndex()
        )

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        item = self._get_item(index)
        node_data = get_item_data(item)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if isinstance(node_data, SequenceNode):
            flags |= Qt.ItemFlag.ItemNeverHasChildren
        return flags

    def get_path(self, index: QModelIndex) -> PureSequencePath:
        item = self._get_item(index)
        node_data = get_item_data(item)
        return node_data.path

    def _get_item(self, index) -> QStandardItem:
        result = (
            index.internalPointer()
            if index.isValid()
            else self.tree.invisibleRootItem()
        )
        assert isinstance(result, QStandardItem)
        return result

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
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
                        self.handle_folder_became_sequence(parent, session)
                        return
                    except PathNotFoundError:
                        self.handle_path_was_deleted(parent)
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
                SequenceNode(
                    path=path,
                    stats=stats,
                    creation_date=creation_date,
                    last_query_time=get_update_date(),
                ),
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

    @staticmethod
    async def _build_item_async(
        path: PureSequencePath, session: AsyncExperimentSession
    ) -> QStandardItem:
        assert await session.paths.does_path_exists(path)
        item = QStandardItem()
        item.setData(path.name, Qt.DisplayRole)
        is_sequence = unwrap(await session.sequences.is_sequence(path))
        creation_date = unwrap(await session.paths.get_path_creation_date(path))
        if is_sequence:
            stats = unwrap(await session.sequences.get_stats(path))
            item.setData(
                SequenceNode(
                    path=path,
                    stats=stats,
                    creation_date=creation_date,
                    last_query_time=get_update_date(),
                ),
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
        return 5

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return "Name"
                elif section == 1:
                    return "Status"
                elif section == 2:
                    return "Progress"
                elif section == 3:
                    return "Duration"
                elif section == 4:
                    return "Date created"
            else:
                return section
        return None

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
            if isinstance(node_data, SequenceNode):
                return format_duration(node_data.stats, node_data.last_query_time)
            else:
                return None
        elif index.column() == 4:
            return QDateTime(node_data.creation_date.astimezone(None))  # type: ignore

    async def watch_session(self) -> None:
        while True:
            await self.update_from_session()
            await asyncio.sleep(0)

    async def update_from_session(self) -> None:
        await self.prune()
        await self.add_new_paths()
        for row in range(self.rowCount()):
            await self.update_stats(self.index(row, 0))

    async def update_stats(self, index: QModelIndex) -> None:
        """Update the stats of sequences and folders in the model from the session."""

        if not index.isValid():
            # This situation occurs sometimes, but unsure why.
            # Maybe if fetch is called in the middle of an async call?
            return None

        item = self._get_item(index)
        data = get_item_data(item)
        change_detected = False
        async with self.session_maker.async_session() as session:
            creation_date_result = await session.paths.get_path_creation_date(data.path)
            try:
                creation_date = unwrap(creation_date_result)
            except PathNotFoundError:
                self.handle_path_was_deleted(index)
                return
            if creation_date != data.creation_date:
                data.creation_date = creation_date
                change_detected = True
            if isinstance(data, SequenceNode):
                sequence_stats_result = await session.sequences.get_stats(data.path)
                try:
                    stats = unwrap(sequence_stats_result)
                except PathIsNotSequenceError:
                    await self.handle_sequence_became_folder(index, session)
                    return
                if stats != data.stats:
                    data.stats = stats
                    data.last_query_time = get_update_date()
                    change_detected = True
        if change_detected:
            top_left = index.siblingAtColumn(0)
            bottom_right = index.siblingAtColumn(self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])
        if isinstance(data, FolderNode):
            for row in range(item.rowCount()):
                await self.update_stats(self.index(row, 0, index))

    async def prune(self, parent: QModelIndex = QModelIndex()) -> None:
        """Removes items from the model that no longer exist in the session."""

        parent_item = self._get_item(parent)
        parent_data = get_item_data(parent_item)
        async with self.session_maker.async_session() as session:
            children_result = await session.paths.get_children(parent_data.path)
            try:
                child_paths = unwrap(children_result)
            except PathIsSequenceError:
                await self.handle_folder_became_sequence_async(parent, session)
                return
            except PathNotFoundError:
                self.handle_path_was_deleted(parent)
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

    async def add_new_paths(self, parent: QModelIndex = QModelIndex()) -> None:
        """Add new paths to the model that have been added to the session."""

        parent_item = self._get_item(parent)
        parent_data = get_item_data(parent_item)
        match parent_data:
            case SequenceNode():
                return
            case FolderNode(has_fetched_children=False):
                return
            case FolderNode(path=parent_path, has_fetched_children=True):
                async with self.session_maker.async_session() as session:
                    children_result = await session.paths.get_children(parent_path)
                    try:
                        child_paths = unwrap(children_result)
                    except PathIsSequenceError:
                        await self.handle_folder_became_sequence_async(parent, session)
                        return
                    except PathNotFoundError:
                        self.handle_path_was_deleted(parent)
                        return
                    already_added_paths = {
                        get_item_data(parent_item.child(row)).path
                        for row in range(parent_item.rowCount())
                    }
                    new_paths = child_paths - already_added_paths
                    self.beginInsertRows(
                        parent,
                        parent_item.rowCount(),
                        parent_item.rowCount() + len(new_paths) - 1,
                    )
                    for child_path in new_paths:
                        child_item = await self._build_item_async(child_path, session)
                        parent_item.appendRow(child_item)
                    self.endInsertRows()
                for row in range(self.rowCount(parent)):
                    await self.add_new_paths(self.index(row, 0, parent))

    def handle_folder_became_sequence(
        self, index: QModelIndex, session: ExperimentSession
    ):
        item = self._get_item(index)
        data = get_item_data(item)
        stats = unwrap(session.sequences.get_stats(data.path))
        creation_date = unwrap(session.paths.get_path_creation_date(data.path))
        self.beginRemoveRows(index, 0, item.rowCount() - 1)
        item.setData(
            SequenceNode(
                path=data.path,
                stats=stats,
                creation_date=creation_date,
                last_query_time=get_update_date(),
            ),
            NODE_DATA_ROLE,
        )
        item.removeRows(0, item.rowCount())
        self.endRemoveRows()
        self.emit_index_updated(index)

    async def handle_folder_became_sequence_async(
        self, index: QModelIndex, session: AsyncExperimentSession
    ):
        item = self._get_item(index)
        data = get_item_data(item)
        stats = unwrap(await session.sequences.get_stats(data.path))
        creation_date = unwrap(await session.paths.get_path_creation_date(data.path))
        self.beginRemoveRows(index, 0, item.rowCount() - 1)
        item.setData(
            SequenceNode(
                path=data.path,
                stats=stats,
                creation_date=creation_date,
                last_query_time=get_update_date(),
            ),
            NODE_DATA_ROLE,
        )
        item.removeRows(0, item.rowCount())
        self.endRemoveRows()
        self.emit_index_updated(index)

    def handle_path_was_deleted(self, index: QModelIndex):
        parent = self.parent(index)
        grandparent_item = self._get_item(parent)
        self.beginRemoveRows(parent, index.row(), index.row())
        grandparent_item.removeRow(index.row())
        self.endRemoveRows()

    async def handle_sequence_became_folder(
        self, index: QModelIndex, session: AsyncExperimentSession
    ):
        item = self._get_item(index)
        data = get_item_data(item)
        creation_date = unwrap(await session.paths.get_path_creation_date(data.path))
        assert item.rowCount() == 0
        item.setData(
            FolderNode(
                path=data.path, has_fetched_children=False, creation_date=creation_date
            ),
            NODE_DATA_ROLE,
        )
        self.emit_index_updated(index)

    def emit_index_updated(self, index: QModelIndex) -> None:
        self.dataChanged.emit(
            index.siblingAtColumn(0),
            index.siblingAtColumn(self.columnCount() - 1),
            [Qt.ItemDataRole.DisplayRole],
        )


def format_duration(stats: SequenceStats, updated_time: datetime.datetime) -> str:
    if stats.state == State.DRAFT or stats.state == State.PREPARING:
        return f"--/--"
    elif stats.state == State.RUNNING:
        running_duration = updated_time - stats.start_time
        expected_num_shots = stats.expected_number_shots
        if is_unknown(expected_num_shots) or stats.number_completed_shots == 0:
            remaining = "--"
        else:
            remaining = (
                running_duration
                / stats.number_completed_shots
                * (expected_num_shots - stats.number_completed_shots)
            )
        if isinstance(remaining, datetime.timedelta):
            total = remaining + running_duration
            remaining = _format_seconds(total.total_seconds())
        running_duration = _format_seconds(running_duration.total_seconds())
        return f"{running_duration}/{remaining}"
    elif (
        stats.state == State.FINISHED
        or stats.state == State.CRASHED
        or stats.state == State.INTERRUPTED
    ):
        try:
            total_duration = stats.stop_time - stats.start_time
            total_duration = _format_seconds(total_duration.total_seconds())
            return total_duration
        except TypeError:
            return ""


def _format_seconds(seconds: float) -> str:
    """Format seconds into a string.

    Args:
        seconds: Seconds to format.

    Returns:
        Formatted string.
    """

    seconds = int(seconds)
    result = [f"{seconds % 60}s"]

    minutes = seconds // 60
    if minutes > 0:
        result.append(f"{minutes % 60}m")
        hours = minutes // 60
        if hours > 0:
            result.append(f"{hours % 24}h")
            days = hours // 24
            if days > 0:
                result.append(f"{days}d")

    return ":".join(reversed(result))


def get_update_date() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc).replace(microsecond=0)

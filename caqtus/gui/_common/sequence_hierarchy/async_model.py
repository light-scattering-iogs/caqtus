from __future__ import annotations

import abc
import contextlib
import datetime
import json
import weakref
from collections.abc import Awaitable
from typing import Optional, TypeGuard, assert_never, assert_type, Never, Callable

import anyio
import anyio.abc
import attrs
from PySide6.QtCore import (
    QObject,
    QAbstractItemModel,
    QModelIndex,
    Qt,
    QDateTime,
    QPersistentModelIndex,
    QMimeData,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from caqtus.session import (
    ExperimentSessionMaker,
    PureSequencePath,
    ExperimentSession,
    AsyncExperimentSession,
    PathIsRootError,
)
from caqtus.session import (
    PathNotFoundError,
    PathIsSequenceError,
    PathIsNotSequenceError,
    State,
)
from caqtus.session._sequence_collection import SequenceStats
from caqtus.types.iteration import (
    Unknown,
    IterationConfiguration,
)
from caqtus.types.timelane import TimeLanes
from caqtus.utils._result import Result, is_failure, Failure, Success

NODE_DATA_ROLE = Qt.ItemDataRole.UserRole + 1

DEFAULT_INDEX = QModelIndex()


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
        self._background_runner = BackgroundRunner(self.watch_session)

    def index(self, row, column, parent=DEFAULT_INDEX):
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

    def parent(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, index: QModelIndex | QPersistentModelIndex = DEFAULT_INDEX
    ):
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

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags | Qt.ItemFlag.ItemIsDropEnabled
        item = self._get_item(index)
        node_data = get_item_data(item)
        flags = Qt.ItemFlag.NoItemFlags
        if isinstance(node_data, SequenceNode):
            flags |= Qt.ItemFlag.ItemIsEnabled
            flags |= Qt.ItemFlag.ItemIsSelectable
            flags |= Qt.ItemFlag.ItemNeverHasChildren
            if node_data.stats.state not in {State.PREPARING, State.RUNNING}:
                flags |= Qt.ItemFlag.ItemIsDragEnabled
        else:
            assert_type(node_data, FolderNode)
            if index.column() == 0:
                flags |= Qt.ItemFlag.ItemIsSelectable
                flags |= Qt.ItemFlag.ItemIsEnabled
                flags |= Qt.ItemFlag.ItemIsDragEnabled
                flags |= Qt.ItemFlag.ItemIsDropEnabled
            if index.column() == 4:
                flags |= Qt.ItemFlag.ItemIsSelectable
                flags |= Qt.ItemFlag.ItemIsEnabled
        return flags

    def mimeTypes(self):  # noqa: N802
        return ["application/x-caqtus-sequence-path"]

    def mimeData(self, indexes):  # noqa: N802
        items = [self._get_item(index) for index in indexes]
        data = [get_item_data(item) for item in items]
        paths = {node.path for node in data}
        assert len(paths) == 1
        encoded = json.dumps([str(path) for path in paths]).encode("utf-8")
        mime_data = QMimeData()
        mime_data.setData("application/x-caqtus-sequence-path", encoded)
        return mime_data

    def supportedDropActions(self):  # noqa: N802
        return Qt.DropAction.MoveAction

    def canDropMimeData(self, data, action, row, column, parent):  # noqa: N802
        if not data.hasFormat("application/x-caqtus-sequence-path"):
            return False
        if action != Qt.DropAction.MoveAction:
            return False
        parent_item = self._get_item(parent)
        node_data = get_item_data(parent_item)
        if row == -1:
            return isinstance(node_data, FolderNode)
        return False

    def dropMimeData(self, data, action, row, column, parent):  # noqa: N802
        if not self.canDropMimeData(data, action, row, column, parent):
            return False

        paths = json.loads(
            bytes(
                data.data(
                    "application/x-caqtus-sequence-path"
                )  # pyright: ignore[reportArgumentType]
            ).decode("utf-8")
        )
        assert len(paths) == 1
        src = PureSequencePath(paths[0])
        if row == -1:
            dst_parent = get_item_data(self._get_item(parent)).path
            dst = dst_parent / src.name
            with self.session_maker() as session, self._background_runner.suspend():
                result = session.paths.move(src, dst)
                return result.is_success()
        return False

    def removeRows(self, row, count, parent=...):  # noqa: N802
        # This method only remove the in-memory data, it does not remove the path from
        # the session.
        parent_item = self._get_item(parent)
        with self._background_runner.suspend():
            self.beginRemoveRows(parent, row, row + count - 1)
            parent_item.removeRows(row, count)
            self.endRemoveRows()
        return True

    def _get_item(self, index) -> QStandardItem:
        result = (
            index.internalPointer()
            if index.isValid()
            else self.tree.invisibleRootItem()
        )
        assert isinstance(result, QStandardItem)
        return result

    def rowCount(self, parent=DEFAULT_INDEX) -> int:  # noqa: N802
        if parent.column() > 0:
            return 0
        parent_item = self._get_item(parent)
        node_data = get_item_data(parent_item)
        if isinstance(node_data, SequenceNode):
            return 0
        else:
            assert_type(node_data, FolderNode)
            if node_data.has_fetched_children:
                return parent_item.rowCount()
            else:
                return 0

    def hasChildren(self, parent=DEFAULT_INDEX) -> bool:  # noqa: N802
        parent_item = self._get_item(parent)
        node_data = get_item_data(parent_item)
        if isinstance(node_data, SequenceNode):
            return False
        else:
            assert_type(node_data, FolderNode)
            if node_data.has_fetched_children:
                return parent_item.rowCount() > 0
            else:
                return True

    def canFetchMore(self, parent) -> bool:  # noqa: N802
        parent_item = self._get_item(parent)
        node_data = get_item_data(parent_item)
        match node_data:
            case SequenceNode():
                return False
            case FolderNode(has_fetched_children=already_fetched):
                return not already_fetched

    def fetchMore(self, parent):  # noqa: N802
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
                        children = children_result.unwrap()
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
        item.setData(path.name, Qt.ItemDataRole.DisplayRole)
        is_sequence = session.sequences.is_sequence(path).unwrap()
        creation_date = session.paths.get_path_creation_date(path).unwrap()
        if is_sequence:
            stats = session.sequences.get_stats(path).unwrap()
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
        item.setData(path.name, Qt.ItemDataRole.DisplayRole)
        is_sequence = (await session.sequences.is_sequence(path)).unwrap()
        creation_date = (await session.paths.get_path_creation_date(path)).unwrap()
        if is_sequence:
            stats = (await session.sequences.get_stats(path)).unwrap()
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

    def columnCount(self, parent=DEFAULT_INDEX) -> int:  # noqa: N802
        return 5

    def headerData(  # noqa: N802
        self, section, orientation, role=Qt.ItemDataRole.DisplayRole
    ):
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

    async def run(self) -> Never:
        await self._background_runner.run()

    async def watch_session(self) -> None:
        while True:
            # The call to update_from_session must be safe to be cancelled in the
            # middle of its execution, without corrupting the model.
            await self.update_from_session()

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
                creation_date = creation_date_result.unwrap()
            except PathNotFoundError:
                await self.handle_path_was_deleted_async(index)
                return
            if creation_date != data.creation_date:
                await anyio.sleep(0)  # noqa: ASYNC115
                data.creation_date = creation_date
                change_detected = True
            if isinstance(data, SequenceNode):
                sequence_stats_result = await session.sequences.get_stats(data.path)
                try:
                    stats = sequence_stats_result.unwrap()
                except PathIsNotSequenceError:
                    await self.handle_sequence_became_folder(index, session)
                    return
                if stats != data.stats:
                    await anyio.sleep(0)  # noqa: ASYNC115
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

    async def prune(self, parent: QModelIndex = DEFAULT_INDEX) -> None:
        """Removes children of the parent that are no longer present in the session."""

        parent_item = self._get_item(parent)
        parent_data = get_item_data(parent_item)

        if isinstance(parent_data, SequenceNode):
            return

        async with self.session_maker.async_session() as session:
            children_result = await session.paths.get_children(parent_data.path)
            await anyio.sleep(0)  # noqa: ASYNC115
            try:
                child_paths = children_result.unwrap()
            except PathIsSequenceError:
                await self.handle_folder_became_sequence_async(parent, session)
                return
            except PathNotFoundError:
                await self.handle_path_was_deleted_async(parent)
                return

        await anyio.sleep(0)  # noqa: ASYNC115
        # Need to use persistent indices to avoid invalidation while removing rows.
        child_indices = set[QPersistentModelIndex]()
        for row in range(self.rowCount(parent)):
            child_indices.add(QPersistentModelIndex(self.index(row, 0, parent)))

        remaining_children = set()
        for child in child_indices:
            child_item = self._get_item(child)
            child_path = get_item_data(child_item).path
            if child_path not in child_paths:
                self.beginRemoveRows(parent, child.row(), child.row())
                parent_item.removeRow(child.row())
                self.endRemoveRows()
            else:
                remaining_children.add(child)

        for child in remaining_children:
            await self.prune(QModelIndex(child))

    async def add_new_paths(self, parent: QModelIndex = DEFAULT_INDEX) -> None:
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
                        child_paths = children_result.unwrap()
                    except PathIsSequenceError:
                        await self.handle_folder_became_sequence_async(parent, session)
                        return
                    except PathNotFoundError:
                        await self.handle_path_was_deleted_async(parent)
                        return
                    already_added_paths = {
                        get_item_data(parent_item.child(row)).path
                        for row in range(parent_item.rowCount())
                    }
                    new_paths = child_paths - already_added_paths
                    new_items = [
                        await self._build_item_async(path, session)
                        for path in new_paths
                    ]
                    await self.append_items(parent, new_items)
                for row in range(self.rowCount(parent)):
                    await self.add_new_paths(self.index(row, 0, parent))

    async def append_items(
        self, parent: QModelIndex, items: list[QStandardItem]
    ) -> None:
        await anyio.sleep(0)  # noqa: ASYNC115
        parent_item = self._get_item(parent)
        self.beginInsertRows(
            parent,
            parent_item.rowCount(),
            parent_item.rowCount() + len(items) - 1,
        )
        for item in items:
            parent_item.appendRow(item)
        self.endInsertRows()

    def handle_folder_became_sequence(
        self, index: QModelIndex | QPersistentModelIndex, session: ExperimentSession
    ):
        item = self._get_item(index)
        data = get_item_data(item)
        stats = session.sequences.get_stats(data.path).unwrap()
        creation_date = session.paths.get_path_creation_date(data.path).unwrap()
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
        stats = (await session.sequences.get_stats(data.path)).unwrap()
        creation_date = (await session.paths.get_path_creation_date(data.path)).unwrap()
        await anyio.sleep(0)  # noqa: ASYNC115
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

    def handle_path_was_deleted(
        self, index: QModelIndex | QPersistentModelIndex
    ) -> None:
        parent = self.parent(index)
        parent_item = self._get_item(parent)
        self.beginRemoveRows(parent, index.row(), index.row())
        parent_item.removeRow(index.row())
        self.endRemoveRows()

    async def handle_path_was_deleted_async(self, index: QModelIndex) -> None:
        await anyio.sleep(0)  # noqa: ASYNC115
        self.handle_path_was_deleted(index)

    def get_path(self, index: QModelIndex | QPersistentModelIndex) -> PureSequencePath:
        return get_item_data(self._get_item(index)).path

    async def handle_sequence_became_folder(
        self, index: QModelIndex, session: AsyncExperimentSession
    ):
        item = self._get_item(index)
        data = get_item_data(item)
        creation_date = (await session.paths.get_path_creation_date(data.path)).unwrap()
        assert item.rowCount() == 0
        await anyio.sleep(0)  # noqa: ASYNC115
        item.setData(
            FolderNode(
                path=data.path, has_fetched_children=False, creation_date=creation_date
            ),
            NODE_DATA_ROLE,
        )
        self.emit_index_updated(index)

    def emit_index_updated(self, index: QModelIndex | QPersistentModelIndex) -> None:
        index = QModelIndex(index)
        self.dataChanged.emit(
            index.siblingAtColumn(0),
            index.siblingAtColumn(self.columnCount() - 1),
            [Qt.ItemDataRole.DisplayRole],
        )

    def rename(self, index: QModelIndex, new_name: str) -> Result[None, Exception]:
        """Rename a sequence or folder in the model.

        Args:
            index: Index of the sequence or folder to rename.
                It must be a valid index.
            new_name: The new name to give to the path.
                It must be a valid path name.
        """

        if not index.isValid():
            raise ValueError("Invalid index")

        item = self._get_item(index)
        data = get_item_data(item)

        # Since the index is valid, it can't be the root item, and thus it must have a
        # parent.
        assert data.path.parent is not None
        new_path = data.path.parent / new_name

        with self.session_maker() as session, self._background_runner.suspend():
            result = session.paths.move(data.path, new_path)
            if result.is_success():
                self._rename_recursively(index, new_path)
            return result

    def _rename_recursively(
        self, index: QModelIndex, new_prefix: PureSequencePath
    ) -> None:
        item = self._get_item(index)
        data = get_item_data(item)
        new_parts = new_prefix.parts + data.path.parts[len(new_prefix.parts) :]
        new_path = PureSequencePath.from_parts(new_parts)
        data.path = new_path
        self.emit_index_updated(index)
        for row in range(self.rowCount(index)):
            self._rename_recursively(self.index(row, 0, index), new_path)

    def create_new_sequence(
        self,
        parent: QModelIndex,
        name: str,
        iteration_config: IterationConfiguration,
        time_lanes: TimeLanes,
    ) -> Result[None, Exception]:
        parent_item = self._get_item(parent)
        parent_data = get_item_data(parent_item)
        if not isinstance(parent_data, FolderNode):
            raise ValueError("Parent must be a folder")
        new_path = parent_data.path / name
        with self.session_maker() as session, self._background_runner.suspend():
            creation_result = session.sequences.create(
                new_path, iteration_config, time_lanes
            )
            if is_failure(creation_result):
                return creation_result
            item = self._build_item(new_path, session)
            self.beginInsertRows(parent, parent_item.rowCount(), parent_item.rowCount())
            parent_item.appendRow(item)
            self.endInsertRows()
            return creation_result

    def remove_path(
        self, index: QModelIndex
    ) -> (
        Success[None]
        | Failure[PathNotFoundError]
        | Failure[PathIsSequenceError]
        | Failure[PathIsRootError]
    ):
        """Remove the path at the requested index."""

        item = self._get_item(index)
        path = get_item_data(item).path
        with self.session_maker() as session:
            is_sequence_result = session.sequences.is_sequence(path)
            if is_failure(is_sequence_result):
                return is_sequence_result
            with self._background_runner.suspend():
                if is_sequence_result.value:
                    result = session.paths.delete_path(path, delete_sequences=True)
                else:
                    result = session.paths.delete_path(path, delete_sequences=False)
            if result.is_success():
                assert self.removeRows(index.row(), 1, self.parent(index))
                return Success(None)
            else:
                return result


def format_duration(stats: SequenceStats, updated_time: datetime.datetime) -> str:
    if stats.state == State.DRAFT or stats.state == State.PREPARING:
        return "--/--"
    elif stats.state == State.RUNNING:
        assert stats.start_time is not None
        assert stats.number_completed_shots is not None
        running_duration = updated_time - stats.start_time
        expected_num_shots = stats.expected_number_shots
        if isinstance(expected_num_shots, Unknown) or stats.number_completed_shots == 0:
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
        # Need to handle the case where the sequence crashed before starting.
        if stats.start_time is None or stats.stop_time is None:
            return ""
        else:
            total_duration = stats.stop_time - stats.start_time
            return _format_seconds(total_duration.total_seconds())
    assert_never(stats.state)


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


class BackgroundRunner:
    def __init__(self, task: Callable[[], Awaitable[None]]):
        self.task = task
        self._task_group: Optional[anyio.abc.TaskGroup] = None
        self._cancel_scopes = weakref.WeakValueDictionary[int, anyio.CancelScope]()

    async def run(self) -> Never:
        """Run the background task indefinitely."""

        while True:
            self._can_resume = anyio.Event()
            with anyio.CancelScope() as self._cancel_scope:
                await self.task()
            await self._can_resume.wait()

    @contextlib.contextmanager
    def suspend(self):
        """Suspend the background task until the context manager exits.

        When the context manager is entered, the background task is cancelled at the
        next cancellation point.
        When the context manager exits, a new background task is started.
        """

        self._cancel_scope.cancel()

        yield

        self._can_resume.set()

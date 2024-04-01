from __future__ import annotations

import datetime
import threading
from typing import Optional

from PySide6.QtCore import (
    QAbstractItemModel,
    QThread,
    QModelIndex,
    Qt,
    QTimer,
    Signal,
    QDateTime,
)
from anytree import NodeMixin
from returns.result import Success

from caqtus.session import PureSequencePath, ExperimentSessionMaker, ExperimentSession
from caqtus.session.path_hierarchy import PathNotFoundError
from caqtus.session.result import unwrap, Failure
from caqtus.session.sequence import State
from caqtus.session.sequence_collection import (
    PathIsSequenceError,
    SequenceStats,
    PathIsNotSequenceError,
)
from caqtus.utils import log_exception
from .logger import logger
from typing_extensions import deprecated


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
        self.sequence_stats = None

        self.should_fetch_stats = False

    @property
    def sequence_stats(self) -> Optional[SequenceStats]:
        return self._sequence_stats

    @sequence_stats.setter
    def sequence_stats(self, value: Optional[SequenceStats]):
        self._sequence_stats = value
        if value is not None:
            self.formatted_duration = format_duration(value)
        else:
            self.formatted_duration = None

    @property
    def creation_date(self) -> Optional[datetime.datetime]:
        return self._creation_date

    @creation_date.setter
    def creation_date(self, value: Optional[datetime.datetime]):
        self._creation_date = value
        if value is not None:
            self.formatted_creation_date = QDateTime(value.astimezone(None))
        else:
            self.formatted_creation_date = None

    def row(self):
        if self.parent:
            return self.parent.children.index(self)
        return 0


@deprecated("Use AsyncPathHierarchyModel instead")
class PathHierarchyModel(QAbstractItemModel):
    """A Qt tree model that provides data for a sequence hierarchy.

    This model is used in combination with a QTreeView to display a hierarchy of
    folders and sequences.
    This model automatically populates and updates itself based on the path
    hierarchy and the changes that occur to it.
    It uses a background thread to periodically check for changes in the hierarchy and
    updates the model when changes are found.
    It doesn't provide support for editing the hierarchy, only for displaying it.
    Changes to the hierarchy can be done independently of the model, and the model will
    automatically update itself to reflect the changes.
    This model must be used as a context manager to start watching for changes.
    """

    def __init__(self, session_maker: ExperimentSessionMaker, parent=None):
        """Create a new PathHierarchyModel.

        Args:
            session_maker: A function that returns a new session when called.
            This is used to connect to the experiment storage in which the sequence
            hierarchy is stored.
        """

        super().__init__(parent)
        self._tree_structure_lock = threading.Lock()
        self._root = PathHierarchyItem(PureSequencePath.root(), None, None)
        self._session_maker = session_maker
        self._thread = self.TreeUpdateThread(self, self._session_maker)
        self._thread.item_structure_changed.connect(self.process_structure_change)
        self._thread.data_changed.connect(self.on_data_changed)

    def on_data_changed(self, index: QModelIndex):
        self.dataChanged.emit(
            self.index(index.row(), 0, index.parent()),
            self.index(index.row(), self.columnCount(index) - 1, index.parent()),
        )

    def __enter__(self):
        """Populates the model with paths and start watching for changes."""

        with self._session_maker() as session:
            self.beginResetModel()
            self._root = construct_hierarchy(session)
            self.endResetModel()

        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Stops the background thread that watches for changes in the hierarchy."""

        self._thread.quit()
        self._thread.wait()

    def get_path(self, index: QModelIndex) -> PureSequencePath:
        if not index.isValid():
            return self._root.hierarchy_path
        item = index.internalPointer()  # type: ignore
        assert isinstance(item, PathHierarchyItem)
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

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_item = index.internalPointer()  # type: ignore
        assert isinstance(child_item, PathHierarchyItem)
        parent_item = child_item.parent
        if not parent_item:
            return QModelIndex()
        if parent_item is self._root:
            return QModelIndex()
        return self.createIndex(parent_item.row(), index.column(), parent_item)

    def rowCount(self, parent=QModelIndex()):
        parent_item = self._get_item(parent)
        return len(parent_item.children)

    def hasChildren(self, parent: QModelIndex) -> bool:
        parent_item = self._get_item(parent)
        return bool(parent_item.children)

    def _get_item(self, index: QModelIndex) -> PathHierarchyItem:
        if not index.isValid():
            return self._root
        item = index.internalPointer()
        assert isinstance(item, PathHierarchyItem)
        return item

    def columnCount(self, parent=QModelIndex()):
        return 5

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        item = index.internalPointer()
        assert isinstance(item, PathHierarchyItem)
        if item.sequence_stats is not None:
            flags |= Qt.ItemFlag.ItemNeverHasChildren
        return flags

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
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

        item = self._get_item(index)

        if item is self._root:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            item.should_fetch_stats = True
            if index.column() == 0:
                return item.hierarchy_path.name
            elif index.column() == 1:
                return item.sequence_stats
            elif index.column() == 2:
                if item.sequence_stats is None:
                    return None
                else:
                    completed = item.sequence_stats.number_completed_shots
                    total = item.sequence_stats.expected_number_shots
                    return f"{completed}/{total}"
            elif index.column() == 3:
                return item.formatted_duration
            elif index.column() == 4:
                return item.formatted_creation_date
        return None

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

    def process_structure_change(self, parent: QModelIndex):
        if not parent.isValid():
            parent_item = self._root
        else:
            parent_item = parent.internalPointer()  # type: ignore
            assert isinstance(parent_item, PathHierarchyItem)

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
        item_structure_changed = Signal(QModelIndex)
        data_changed = Signal(QModelIndex)

        def __init__(
            self,
            parent: PathHierarchyModel,
            session_maker: ExperimentSessionMaker,
        ):
            super().__init__(parent)
            self._parent = parent
            self.lock = parent._tree_structure_lock
            self.session = session_maker()

        @property
        def root(self) -> PathHierarchyItem:
            return self._parent._root

        def run(self):
            timer = QTimer()

            @log_exception(logger)
            def update():
                with self.lock, self.session:
                    try:
                        self.check_item_change(QModelIndex())
                    except PathNotFoundError:
                        pass
                    except FoundChange as e:
                        self.item_structure_changed.emit(e.index)

            timer.timeout.connect(update)  # type: ignore
            timer.start(50)
            self.exec()
            timer.stop()

        def check_item_change(self, index: QModelIndex) -> None:
            path_item = self._parent._get_item(index)

            self.check_path_data_changed(index)
            path = path_item.hierarchy_path
            try:
                fetched_child_paths = unwrap(self.session.paths.get_children(path))
            except PathIsSequenceError:
                return
            present_child_paths = {child.hierarchy_path for child in path_item.children}
            if fetched_child_paths != present_child_paths:
                logger.debug(
                    f"Found change in %s: "
                    f"fetched_child_paths=%s vs present_child_paths=%s",
                    path,
                    fetched_child_paths,
                    present_child_paths,
                )
                raise FoundChange(index)
            else:
                for child in path_item.children:
                    child_index = self._parent.index(child.row(), 0, index)
                    self.check_item_change(child_index)

        def check_path_data_changed(self, index: QModelIndex) -> None:
            if not index.isValid():
                return
            else:
                path_item = index.internalPointer()
                assert isinstance(path_item, PathHierarchyItem)
                if not path_item.should_fetch_stats:
                    return
                path = path_item.hierarchy_path
                creation_date = unwrap(self.session.paths.get_path_creation_date(path))
                if creation_date != path_item.creation_date:
                    path_item.creation_date = creation_date
                try:
                    sequence_stats = unwrap(self.session.sequences.get_stats(path))
                except PathIsNotSequenceError:
                    sequence_stats = None
                if sequence_stats != path_item.sequence_stats:
                    path_item.sequence_stats = sequence_stats
                path_item.should_fetch_stats = False
                self.data_changed.emit(index)

        # def check_sequence_stats_changed(self, index: QModelIndex) -> bool:
        #     if not index.isValid():
        #         return False
        #     else:
        #         path_item = index.internalPointer()
        #         assert isinstance(path_item, PathHierarchyItem)
        #         if path_item.should_fetch_stats:
        #             path = path_item.hierarchy_path
        #             try:
        #                 sequence_stats = unwrap(self.session.sequences.get_stats(path))
        #             except PathIsNotSequenceError:
        #                 sequence_stats = None
        #             if sequence_stats != path_item.sequence_stats:
        #                 path_item.sequence_stats = sequence_stats
        #             path_item.should_fetch_stats = False
        #             self.sequence_stats_changed.emit(index)


class FoundChange(Exception):
    def __init__(self, index: QModelIndex):
        self.index = index


def is_time_zone_aware(dt: datetime.datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def format_duration(stats: SequenceStats) -> str:
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if stats.state == State.DRAFT or stats.state == State.PREPARING:
        return f"--/--"
    elif stats.state == State.RUNNING:
        running_duration = now - stats.start_time
        if stats.expected_number_shots is None or stats.number_completed_shots == 0:
            remaining = "--"
        else:
            remaining = (
                running_duration
                / stats.number_completed_shots
                * (stats.expected_number_shots - stats.number_completed_shots)
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


def construct_hierarchy(session: ExperimentSession) -> PathHierarchyItem:
    root = PathHierarchyItem(PureSequencePath.root(), None, None)
    root.children = construct_children(session, root)
    return root


def construct_children(
    session: ExperimentSession, parent_item: PathHierarchyItem
) -> list[PathHierarchyItem]:
    match session.paths.get_children(parent_item.hierarchy_path):
        case Failure(PathNotFoundError() as e):
            raise e
        case Failure(PathIsSequenceError()):
            return []
        case Success(child_paths):
            child_items = []
            for child_path in child_paths:
                child_item = PathHierarchyItem(
                    child_path,
                    parent_item,
                    unwrap(session.paths.get_path_creation_date(child_path)),
                )
                child_item.children = construct_children(session, child_item)
                if unwrap(session.sequences.is_sequence(child_path)):
                    child_item.sequence_stats = unwrap(
                        session.sequences.get_stats(child_path)
                    )
                session.sequences.get_stats(child_path)
                child_items.append(child_item)
            return child_items

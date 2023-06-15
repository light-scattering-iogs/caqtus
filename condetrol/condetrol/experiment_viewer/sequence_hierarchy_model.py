import copy
import logging
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt
from anytree import NodeMixin

from concurrent_updater import ConcurrentUpdater
from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.configuration import SequenceConfig, SequenceSteps, ShotConfiguration
from sequence.runtime import SequencePath, Sequence, State, SequenceStats

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


class SequenceHierarchyModel(QAbstractItemModel):
    """Tree model used to display the sequences contained in a session.

    This model keep an in memory representation of the sequences hierarchy and update it in a background thread. It
    does not provide any method to create, edit or delete sequences (see EditableSequenceHierarchyModel for that).
    """

    def __init__(self, session_maker: ExperimentSessionMaker, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._session = session_maker()
        self._stats_update_session = session_maker()

        with self._session as session:
            self._root = SequenceHierarchyItem(
                SequencePath.root(),
                children=_build_children_items(SequencePath.root(), session),
                row=0,
                is_sequence=False,
            )
            _update_stats(self._root, session)

        self._stats_updater = ConcurrentUpdater(self._update_stats, watch_interval=0.5)
        self._stats_updater.start()
        self.destroyed.connect(self.on_destroy)

    def on_destroy(self):
        self._stats_updater.stop()

    def _update_stats(self):
        with self._stats_update_session as session:
            _update_stats(self._root, session)

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        elif not parent.isValid():
            return self.createIndex(row, column, self._root.children[row])
        else:
            parent_item: SequenceHierarchyItem = parent.internalPointer()
            if row < len(parent_item.children):
                return self.createIndex(row, column, parent_item.children[row])
            else:
                return QModelIndex()

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()

        child_item: SequenceHierarchyItem = child.internalPointer()
        if child_item.is_root:
            return QModelIndex()
        else:
            return self.createIndex(
                child_item.parent.row, child.column(), child_item.parent
            )

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._root.children)
        else:
            return len(parent.internalPointer().children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 4

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return
        item: SequenceHierarchyItem = index.internalPointer()
        stats = item.sequence_stats

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return self.get_sequence_name(item)
            elif index.column() == 1:
                return stats
            elif index.column() == 2:
                if stats:
                    if (total := stats["total_number_shots"]) is None:
                        total = "--"
                    return f"{stats['number_completed_shots']}/{total}"
            elif index.column() == 3:
                if stats:
                    if (
                        stats["state"] == State.DRAFT
                        or stats["state"] == State.PREPARING
                    ):
                        return f"--/--"
                    elif stats["state"] == State.RUNNING:
                        running_duration = datetime.now() - stats["start_date"]
                        if (
                            stats["total_number_shots"] is None
                            or stats["number_completed_shots"] == 0
                        ):
                            remaining = "--"
                        else:
                            remaining = (
                                running_duration
                                / stats["number_completed_shots"]
                                * (
                                    stats["total_number_shots"]
                                    - stats["number_completed_shots"]
                                )
                            )
                        if isinstance(remaining, timedelta):
                            total = remaining + running_duration
                            remaining = _format_seconds(total.total_seconds())
                        running_duration = _format_seconds(
                            running_duration.total_seconds()
                        )
                        return f"{running_duration}/{remaining}"
                    elif stats["state"] == State.FINISHED:
                        total_duration = stats["stop_date"] - stats["start_date"]
                        total_duration = _format_seconds(total_duration.total_seconds())
                        return total_duration

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Optional[str]:
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            if section == 0:
                return "Name"
            elif section == 1:
                return "Status"
            elif section == 2:
                return "Shots"
            elif section == 3:
                return "Duration"
        return None

    @staticmethod
    def get_sequence_name(item: "SequenceHierarchyItem"):
        return item.sequence_path.name

    def get_sequence_stats(self, index: QModelIndex) -> Optional["SequenceStats"]:
        item: "SequenceHierarchyItem" = index.internalPointer()
        if item.is_sequence:
            with self._session as experiment_session:
                return Sequence(item.sequence_path).get_stats(experiment_session)
        else:
            return None

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
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

        with self._session as session:
            children = _build_children_items(
                parent_item.sequence_path,
                session,
            )

        self.beginInsertRows(parent, 0, len(children) - 1)
        parent_item.children = children
        self.endInsertRows()

    def is_sequence(self, index: QModelIndex) -> bool:
        item: "SequenceHierarchyItem" = index.internalPointer()
        with self._session.activate() as session:
            return item.sequence_path.is_sequence(session)

    @staticmethod
    def get_path(index: QModelIndex) -> Optional[SequencePath]:
        if not index.isValid():
            return None
        else:
            item: "SequenceHierarchyItem" = index.internalPointer()
            return item.sequence_path


class EditableSequenceHierarchyModel(SequenceHierarchyModel):
    """Tree model used to display and edit the sequences contained in a session.

    This model keep an in memory representation of the sequences hierarchy and update it in a background thread.
    """

    def create_new_folder(self, parent: QModelIndex, name: str):
        if parent.isValid():
            parent_item: "SequenceHierarchyItem" = parent.internalPointer()
        else:
            parent_item = self._root
        new_path = parent_item.sequence_path / name

        children = list(parent_item.children)
        new_row = len(children)
        children.append(
            SequenceHierarchyItem(path=new_path, is_sequence=False, row=new_row)
        )
        with self._session.activate() as session:
            number_created_paths = len(new_path.create(session))
            if number_created_paths == 1:
                _logger.info(f'Created new folder "{str(new_path)}"')
                self.beginInsertRows(parent, new_row, new_row)
                parent_item.children = children
                self.endInsertRows()
            elif number_created_paths == 0:
                _logger.warning(
                    f'Path "{str(new_path)}" already exists and was not created'
                )
            elif number_created_paths > 1:
                raise RuntimeError(
                    "Created more than one path and couldn't update the views"
                )

    def create_new_sequence(
        self, parent_index: QModelIndex, name: str
    ) -> Optional[SequencePath]:
        """Attempt to create a new sequence with the given name under the given parent."""

        if parent_index.isValid():
            parent_item: "SequenceHierarchyItem" = parent_index.internalPointer()
        else:
            parent_item = self._root
        new_path = parent_item.sequence_path / name

        children = list(parent_item.children)
        new_row = len(children)
        sequence_config = SequenceConfig(
            program=SequenceSteps(), shot_configurations={"shot": ShotConfiguration()}
        )
        with self._session as session:
            number_created_paths = len(new_path.create(session))
            if number_created_paths == 1:
                Sequence.create_sequence(new_path, sequence_config, None, session)
                new_child = SequenceHierarchyItem(
                    path=new_path,
                    is_sequence=True,
                    row=new_row,
                )
                children.append(new_child)
                self.beginInsertRows(parent_index, new_row, new_row)
                parent_item.children = children
                self.endInsertRows()
                return new_path
            elif number_created_paths == 0:
                _logger.warning(
                    f'Path "{str(new_path)}" already exists and was not created'
                )
            elif number_created_paths > 1:
                raise RuntimeError(
                    "Created more than one path and couldn't update the views"
                )
        return None

    def duplicate_sequence(self, source_index: QModelIndex, target_name: str) -> bool:
        """
        Duplicates a sequence

        Args:
            source_index: The index of the sequence to duplicate
            target_name: The target name of the new sequence in the same folder as the source sequence

        Returns:
            True if the sequence was duplicated, False otherwise

        """
        source_path = Sequence(source_index.internalPointer().sequence_path)
        target_path = self.create_new_sequence(source_index.parent(), target_name)
        if target_path is not None:
            with self._session as session:
                sequence_config = source_path.get_config(session)
                Sequence(target_path).set_config(sequence_config, session)
                return True
        else:
            return False

    def delete(self, index: QModelIndex):
        if not index.isValid():
            return
        parent_index = index.parent()
        if parent_index.isValid():
            parent_item: "SequenceHierarchyItem" = parent_index.internalPointer()
        else:
            parent_item = self._root.children[index.row()]
        if parent_item.is_folder():  # should always be?
            row = index.row()
            new_children = list(parent_item.children)
            new_children.pop(row)
            with self._session as session:
                item: "SequenceHierarchyItem" = index.internalPointer()
                if (
                    item.is_folder()
                ):  # don't want to risk deleting a folder containing many sequences
                    item.sequence_path.delete(session, delete_sequences=False)
                else:
                    item.sequence_path.delete(session, delete_sequences=True)
                self.beginRemoveRows(parent_index, row, row)
                parent_item.children = new_children
                self.endRemoveRows()

    def revert_to_draft(self, index: QModelIndex):
        if not index.isValid():
            return
        item: "SequenceHierarchyItem" = index.internalPointer()
        if item.is_sequence:
            sequence = Sequence(item.sequence_path)
            with self._session as session:
                sequence.set_state(State.DRAFT, session)
            self.dataChanged.emit(index, index)


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
        self._sequence_stats: Optional[SequenceStats] = None
        if children:
            self.children = children

    def __repr__(self):
        return f"{self.__class__.__name__}({self.sequence_path})"

    def __str__(self):
        return str(self.sequence_path)

    def is_folder(self):
        return not self.is_sequence

    @property
    def sequence_stats(self) -> Optional[SequenceStats]:
        return copy.deepcopy(self._sequence_stats)

    def list_sequences(self) -> list[Sequence]:
        """List all sequences under this item"""

        if self.is_sequence:
            return [Sequence(self.sequence_path)]
        else:
            sequences = []
            for child in self.children:
                sequences.extend(child.list_sequences())
            return sequences


def _build_children_items(
    parent: SequencePath, experiment_session: ExperimentSession
) -> list[SequenceHierarchyItem]:
    """Build children items for a parent path.

    Args:
        parent: Parent path to get the children of.
        experiment_session: Activated experiment session in which to query.
    """

    children = parent.get_children(experiment_session)
    sorted_children = sorted(
        children, key=lambda x: x.get_creation_date(experiment_session)
    )
    children_items = [
        SequenceHierarchyItem(
            child,
            row=row,
            is_sequence=child.is_sequence(experiment_session),
        )
        for row, child in enumerate(sorted_children)
    ]

    return children_items


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


def _update_stats(item: SequenceHierarchyItem, session: ExperimentSession):
    """Update the stats for a sequence hierarchy item."""

    stats = Sequence.query_sequence_stats(item.list_sequences(), session)
    _apply_stats(item, stats)


def _apply_stats(item: SequenceHierarchyItem, stats: dict[SequencePath, SequenceStats]):
    """Apply stats to a sequence hierarchy item."""

    if item.is_sequence:
        item._sequence_stats = stats.get(item.sequence_path, None)
    else:
        for child in item.children:
            _apply_stats(child, stats)

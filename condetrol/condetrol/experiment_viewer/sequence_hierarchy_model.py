import logging
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt6.QtGui import QIcon
from anytree import NodeMixin
from sqlalchemy import func

from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.configuration import SequenceConfig, SequenceSteps, ShotConfiguration
from sequence.runtime import SequencePath, Sequence, State, SequenceStats
from sql_model import SequencePathModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SequenceHierarchyModel(QAbstractItemModel):
    """Tree model for sequence hierarchy.

    This model stores an in-memory representation of the database sequence structure.
    """

    def __init__(self, session_maker: ExperimentSessionMaker):
        self._session = session_maker()

        with self._session as session:
            self._root = SequenceHierarchyItem(
                SequencePath.root(),
                children=_build_children(SequencePath.root(), session),
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
        return 4

    def data(self, index: QModelIndex, role: int = ...):
        if not index.isValid():
            return

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return self.get_sequence_name(index.internalPointer())
            elif index.column() == 1:
                stats = self.get_sequence_stats(index)
                return stats
            elif index.column() == 2:
                stats = self.get_sequence_stats(index)
                if stats:
                    if (total := stats["total_number_shots"]) is None:
                        total = "--"
                    return f"{stats['number_completed_shots']}/{total}"
            elif index.column() == 3:
                stats = self.get_sequence_stats(index)
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

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
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

        with self._session as session:
            children = _build_children(
                parent_item.sequence_path,
                session,
            )

        self.beginInsertRows(parent, 0, len(children) - 1)
        parent_item.children = children
        self.endInsertRows()

    def is_sequence(self, index: QModelIndex) -> bool:
        item: "SequenceHierarchyItem" = index.internalPointer()
        with self._session as session:
            # noinspection PyProtectedMember
            return item.sequence_path._query_model(
                session.get_sql_session()
            ).is_sequence()

    def create_new_folder(self, index: QModelIndex, name: str):
        if index.isValid():
            parent_item: "SequenceHierarchyItem" = index.internalPointer()
        else:
            parent_item = self._root
        new_path = parent_item.sequence_path / name

        children = list(parent_item.children)
        new_row = len(children)
        children.append(
            SequenceHierarchyItem(path=new_path, is_sequence=False, row=new_row)
        )
        with self._session as session:
            number_created_paths = len(new_path.create(session))
            if number_created_paths == 1:
                self.beginInsertRows(index, new_row, new_row)
                parent_item.children = children
                self.endInsertRows()
            elif number_created_paths == 0:
                logger.warning(
                    f'Path "{str(new_path)}" already exists and was not created'
                )
            elif number_created_paths > 1:
                raise RuntimeError(
                    "Created more than one path and couldn't update the views"
                )

    def create_new_sequence(
        self, index: QModelIndex, name: str
    ) -> Optional[SequencePath]:
        if index.isValid():
            parent_item: "SequenceHierarchyItem" = index.internalPointer()
        else:
            parent_item = self._root
        new_path = parent_item.sequence_path / name

        children = list(parent_item.children)
        new_row = len(children)
        children.append(
            SequenceHierarchyItem(path=new_path, is_sequence=True, row=new_row)
        )
        sequence_config = SequenceConfig(
            program=SequenceSteps(), shot_configurations={"shot": ShotConfiguration()}
        )
        with self._session as session:
            number_created_paths = len(new_path.create(session))
            if number_created_paths == 1:
                Sequence.create_sequence(new_path, sequence_config, None, session)
                self.beginInsertRows(index, new_row, new_row)
                parent_item.children = children
                self.endInsertRows()
                return new_path
            elif number_created_paths == 0:
                logger.warning(
                    f'Path "{str(new_path)}" already exists and was not created'
                )
            elif number_created_paths > 1:
                raise RuntimeError(
                    "Created more than one path and couldn't update the views"
                )

    def duplicate_sequence(self, source_index: QModelIndex, target_name: str):
        source_path = Sequence(source_index.internalPointer().sequence_path)
        target_path = self.create_new_sequence(source_index.parent(), target_name)
        if target_path is not None:
            with self._session as session:
                sequence_config = source_path.get_config(session)
                Sequence(target_path).set_config(sequence_config, session)

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

    @staticmethod
    def get_path(index: QModelIndex) -> Optional[SequencePath]:
        if not index.isValid():
            return None
        else:
            item: "SequenceHierarchyItem" = index.internalPointer()
            return item.sequence_path

    def revert_to_draft(self, index: QModelIndex):
        if not index.isValid():
            return
        item: "SequenceHierarchyItem" = index.internalPointer()
        if item.is_sequence:
            sequence = Sequence(item.sequence_path)
            with self._session as session:
                sequence.set_state(State.DRAFT, session)
            self.dataChanged.emit(index, index)

    def fileIcon(self, index: QModelIndex) -> QIcon:
        if not index.isValid():
            return None
        item: "SequenceHierarchyItem" = index.internalPointer()
        if item.is_sequence:
            return QIcon(":/icons/sequence")
        else:
            return None


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


def _build_children(
    parent: SequencePath, experiment_session: ExperimentSession
) -> list[SequenceHierarchyItem]:

    session = experiment_session.get_sql_session()

    children_items = []

    if parent.is_root():
        query_children = (
            session.query(SequencePathModel)
            .filter(func.nlevel(SequencePathModel.path) == 1)
            .order_by(SequencePathModel.creation_date)
        )
        children = session.scalars(query_children)
    else:
        # noinspection PyProtectedMember
        path = parent._query_model(session)
        children = path.children
        children.sort(key=lambda x: x.creation_date)

    for child in children:
        child: SequencePathModel
        children_items.append(
            SequenceHierarchyItem(
                SequencePath(str(child.path)),
                row=len(children_items),
                is_sequence=child.is_sequence(),
            )
        )
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

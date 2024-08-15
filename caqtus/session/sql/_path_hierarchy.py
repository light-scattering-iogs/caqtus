from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING

import sqlalchemy.orm
from attr import frozen
from returns.result import Success, Failure, Result
from sqlalchemy import select
from sqlalchemy.orm import Session

from ._path_table import SQLSequencePath
from .._return_or_raise import unwrap, is_success
from .._path import PureSequencePath
from .._path_hierarchy import (
    PathNotFoundError,
    PathIsRootError,
    PathHierarchy,
)
from .._sequence_collection import PathIsSequenceError

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@frozen
class SQLPathHierarchy(PathHierarchy):
    parent_session: "SQLExperimentSession"

    def does_path_exists(self, path: PureSequencePath) -> bool:
        return _does_path_exists(self._get_sql_session(), path)

    def create_path(
        self, path: PureSequencePath
    ) -> Result[list[PureSequencePath], PathIsSequenceError]:
        paths_to_create: list[PureSequencePath] = []
        current = path
        sequence_collection = self.parent_session.sequences
        while parent := current.parent:
            match sequence_collection.is_sequence(current):
                case Success(True):
                    return Failure(
                        PathIsSequenceError(
                            f"Cannot create path {path} because {current} is already a"
                            " sequence"
                        )
                    )
                case Success(False):
                    pass
                case Failure(PathNotFoundError()):
                    paths_to_create.append(current)
            current = parent

        session = self._get_sql_session()
        created_paths = []
        for path_to_create in reversed(paths_to_create):
            parent = (
                unwrap(self._query_path_model(path_to_create.parent))
                if not path_to_create.parent.is_root()
                else None
            )
            new_path = SQLSequencePath(
                path=str(path_to_create),
                parent=parent,
                creation_date=datetime.now(tz=timezone.utc).replace(tzinfo=None),
            )
            session.add(new_path)
            created_paths.append(path_to_create)
        return Success(created_paths)

    def get_children(
        self, path: PureSequencePath
    ) -> Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
        return _get_children(self._get_sql_session(), path)

    def delete_path(self, path: PureSequencePath, delete_sequences: bool = False):
        session = self._get_sql_session()

        if not delete_sequences:
            sequence_collection = self.parent_session.sequences
            if contained := sequence_collection.get_contained_sequences(path):
                raise PathIsSequenceError(
                    f"Cannot delete a path that contains sequences: {contained}"
                )

        session.delete(unwrap(self._query_path_model(path)))
        session.flush()

    def get_all_paths(self) -> set[PureSequencePath]:
        query = select(SQLSequencePath)
        result = self._get_sql_session().execute(query)
        return {PureSequencePath(path.path) for path in result.scalars()}

    def update_creation_date(self, path: PureSequencePath, date: datetime) -> None:
        if path.is_root():
            raise PathIsRootError(path)

        sql_path = unwrap(self._query_path_model(path))
        sql_path.creation_date = date

    def _query_path_model(
        self, path: PureSequencePath
    ) -> Result[SQLSequencePath, PathNotFoundError]:
        return _query_path_model(self._get_sql_session(), path)

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()

    def get_path_creation_date(
        self, path: PureSequencePath
    ) -> Result[datetime, PathNotFoundError]:
        return _get_path_creation_date(self._get_sql_session(), path)


def _does_path_exists(session: Session, path: PureSequencePath) -> bool:
    if path.is_root():
        return True
    result = _query_path_model(session, path)
    return is_success(result)


def _get_children(
    session: Session, path: PureSequencePath
) -> Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
    if path.is_root():
        query_children = select(SQLSequencePath).where(
            SQLSequencePath.parent_id.is_(None)
        )
        children = session.scalars(query_children)
    else:
        query_result = _query_path_model(session, path)
        match query_result:
            case Success(path_sql):
                if path_sql.sequence:
                    return Failure(
                        PathIsSequenceError(
                            f"Cannot check children of a sequence: {path}"
                        )
                    )
                else:
                    children = path_sql.children
            case Failure() as failure:
                return failure
    # noinspection PyUnboundLocalVariable
    return Success(set(PureSequencePath(str(child.path)) for child in children))


def _get_path_creation_date(
    session: Session, path: PureSequencePath
) -> Result[datetime, PathNotFoundError]:
    if path.is_root():
        return Failure(PathIsRootError(path))
    return _query_path_model(session, path).map(
        lambda x: x.creation_date.replace(tzinfo=timezone.utc)
    )


def _query_path_model(
    session: Session, path: PureSequencePath
) -> Result[SQLSequencePath, PathNotFoundError]:
    stmt = select(SQLSequencePath).where(SQLSequencePath.path == str(path))
    result = session.execute(stmt)
    if found := result.scalar():
        return Success(found)
    else:
        return Failure(PathNotFoundError(path))

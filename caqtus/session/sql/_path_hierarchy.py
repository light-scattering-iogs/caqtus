from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING, assert_never

import sqlalchemy.orm
from attr import frozen
from sqlalchemy import select
from sqlalchemy.orm import Session

from ._path_table import SQLSequencePath
from .._light_result import _Result, _Success, _Failure
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
    ) -> _Result[list[PureSequencePath], PathIsSequenceError]:
        paths_to_create: list[PureSequencePath] = []
        current = path
        sequence_collection = self.parent_session.sequences
        while parent := current.parent:
            is_sequence_result = sequence_collection.is_sequence(current)
            match is_sequence_result:
                case _Success(is_sequence):
                    if is_sequence:
                        return _Failure(
                            PathIsSequenceError(
                                f"Cannot create path {path} because {current} is "
                                f"already a sequence"
                            )
                        )
                case _Failure(PathNotFoundError()):
                    paths_to_create.append(current)
                case _:
                    assert_never(is_sequence_result)
            current = parent

        session = self._get_sql_session()
        created_paths = []
        for path_to_create in reversed(paths_to_create):
            assert path_to_create.parent is not None
            parent_model_result = _query_path_model(session, path_to_create.parent)
            if isinstance(parent_model_result, _Failure):
                assert isinstance(parent_model_result.error, PathIsRootError)
                parent_model = None
            else:
                parent_model = parent_model_result.value

            new_path = SQLSequencePath(
                path=str(path_to_create),
                parent=parent_model,
                creation_date=datetime.now(tz=timezone.utc).replace(tzinfo=None),
            )
            session.add(new_path)
            created_paths.append(path_to_create)
        return _Success(created_paths)

    def get_children(
        self, path: PureSequencePath
    ) -> _Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
        return _get_children(self._get_sql_session(), path)

    def delete_path(self, path: PureSequencePath, delete_sequences: bool = False):
        session = self._get_sql_session()

        if not delete_sequences:
            sequence_collection = self.parent_session.sequences
            if contained := sequence_collection.get_contained_sequences(path).unwrap():
                raise PathIsSequenceError(
                    f"Cannot delete a path that contains sequences: {contained}"
                )
        session.delete(self._query_path_model(path).unwrap())
        session.flush()

    def get_all_paths(self) -> set[PureSequencePath]:
        query = select(SQLSequencePath)
        result = self._get_sql_session().execute(query)
        return {PureSequencePath(path.path) for path in result.scalars()}

    def update_creation_date(self, path: PureSequencePath, date: datetime) -> None:
        if path.is_root():
            raise PathIsRootError(path)

        sql_path = self._query_path_model(path).unwrap()
        sql_path.creation_date = date

    def _query_path_model(
        self, path: PureSequencePath
    ) -> _Result[SQLSequencePath, PathNotFoundError | PathIsRootError]:
        return _query_path_model(self._get_sql_session(), path)

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()

    def get_path_creation_date(
        self, path: PureSequencePath
    ) -> _Result[datetime, PathNotFoundError | PathIsRootError]:
        return _get_path_creation_date(self._get_sql_session(), path)


def _does_path_exists(session: Session, path: PureSequencePath) -> bool:
    if path.is_root():
        return True
    result = _query_path_model(session, path)
    return isinstance(result, _Success)


def _get_children(
    session: Session, path: PureSequencePath
) -> _Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
    query_result = _query_path_model(session, path)
    if isinstance(query_result, _Success):
        path_sql = query_result.unwrap()
        if path_sql.sequence:
            return _Failure(PathIsSequenceError(str(path)))
        else:
            children = path_sql.children
    elif isinstance(query_result, _Failure):
        if isinstance(query_result.error, PathIsRootError):
            query_children = select(SQLSequencePath).where(
                SQLSequencePath.parent_id.is_(None)
            )
            children = session.scalars(query_children)
        elif isinstance(query_result.error, PathNotFoundError):
            return _Failure(query_result.error)
        else:
            assert_never(query_result.error)
    else:
        assert_never(query_result)

    return _Success(set(PureSequencePath(str(child.path)) for child in children))


def _get_path_creation_date(
    session: Session, path: PureSequencePath
) -> _Result[datetime, PathNotFoundError | PathIsRootError]:
    if path.is_root():
        return _Failure(PathIsRootError(path))
    return _query_path_model(session, path).map(
        lambda x: x.creation_date.replace(tzinfo=timezone.utc)
    )


def _query_path_model(
    session: Session, path: PureSequencePath
) -> _Result[SQLSequencePath, PathNotFoundError | PathIsRootError]:
    if path.is_root():
        return _Failure(PathIsRootError(path))
    stmt = select(SQLSequencePath).where(SQLSequencePath.path == str(path))
    result = session.execute(stmt)
    if found := result.scalar():
        return _Success(found)
    else:
        return _Failure(PathNotFoundError(f'Path "{path}" does not exists'))

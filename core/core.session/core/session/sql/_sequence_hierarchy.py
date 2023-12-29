from datetime import datetime
from datetime import timezone
from typing import TYPE_CHECKING

import sqlalchemy.orm
from attr import frozen
from returns.result import Success, Failure, Result
from sqlalchemy import select

from ._path_table import SQLSequencePath
from .._return_or_raise import unwrap, is_success
from ..path import PathNotFoundError
from ..path import PureSequencePath
from ..sequence_file_system import (
    PathIsSequenceError,
    SequenceHierarchy,
)

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@frozen
class SQLSequenceHierarchy(SequenceHierarchy):
    parent_session: "SQLExperimentSession"

    def does_path_exists(self, path: PureSequencePath) -> bool:
        if path.is_root():
            return True
        result = self._query_path_model(path)
        return is_success(result)

    def create_path(
        self, path: PureSequencePath
    ) -> Result[list[PureSequencePath], PathIsSequenceError]:
        paths_to_create: list[PureSequencePath] = []
        current = path
        sequence_collection = self.parent_session.sequence_collection
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
                creation_date=datetime.now(tz=timezone.utc),
            )
            session.add(new_path)
            created_paths.append(path_to_create)
        return Success(created_paths)

    def get_children(
        self, path: PureSequencePath
    ) -> Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
        if path.is_root():
            session = self._get_sql_session()
            query_children = select(SQLSequencePath).where(
                SQLSequencePath.parent_id.is_(None)
            )
            children = session.scalars(query_children)
        else:
            query_result = self._query_path_model(path)
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

    def delete_path(self, path: PureSequencePath, delete_sequences: bool = False):
        session = self._get_sql_session()

        if not delete_sequences:
            sequence_collection = self.parent_session.sequence_collection
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

    def _query_path_model(
        self, path: PureSequencePath
    ) -> Result[SQLSequencePath, PathNotFoundError]:
        stmt = select(SQLSequencePath).where(SQLSequencePath.path == str(path))
        result = self._get_sql_session().execute(stmt)
        if found := result.scalar():
            return Success(found)
        else:
            return Failure(PathNotFoundError(path))

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()

    def get_path_creation_date(
        self, path: PureSequencePath
    ) -> Result[datetime, PathNotFoundError]:
        return self._query_path_model(path).map(lambda x: x.creation_date)

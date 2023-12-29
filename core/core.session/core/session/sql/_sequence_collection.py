from typing import TYPE_CHECKING

import attrs
import sqlalchemy.orm
from returns.result import Result
from returns.result import Success, Failure
from sqlalchemy import select

from ._path_table import SQLSequencePath
from ..path import PathNotFoundError, BoundSequencePath, PureSequencePath
from ..sequence_collection import SequenceCollection

if TYPE_CHECKING:
    from ._experiment_session import SQLExperimentSession


@attrs.frozen
class SQLSequenceCollection(SequenceCollection):
    parent_session: "SQLExperimentSession"

    def is_sequence(self, path: BoundSequencePath) -> Result[bool, PathNotFoundError]:
        return self._query_path_model(path).map(
            lambda path_model: bool(path_model.sequence)
        )

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

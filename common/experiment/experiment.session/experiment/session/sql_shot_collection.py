from datetime import datetime
from typing import Any, TYPE_CHECKING

import sqlalchemy.orm
from attr import frozen
from sqlalchemy import select

from sequence.runtime import Sequence, Shot
from sequence.runtime.shot import ShotNotFoundError
from sql_model import SequenceModel
from sql_model.model import (
    ShotModel,
    DataType,
)
from .experiment_session import (
    ShotCollection,
)

if TYPE_CHECKING:
    from .experiment_session_sql import SQLExperimentSession


@frozen
class SQLShotCollection(ShotCollection):
    parent_session: "SQLExperimentSession"

    def get_shot_data(self, shot: Shot, data_type: DataType) -> dict[str, Any]:
        shot_sql = self._query_shot_model(shot)
        return shot_sql.get_data(data_type, self._get_sql_session())

    def add_shot_data(
        self, shot: Shot, data: dict[str, Any], data_type: DataType
    ) -> None:
        session = self._get_sql_session()
        shot_sql = self._query_shot_model(shot)
        shot_sql.add_data(data, DataType.SCORE, session)
        session.flush()

    def get_shot_start_time(self, shot: Shot) -> datetime:
        shot_sql = self._query_shot_model(shot)
        return shot_sql.start_time

    def get_shot_end_time(self, shot: Shot) -> datetime:
        shot_sql = self._query_shot_model(shot)
        return shot_sql.end_time

    def _query_shot_model(self, shot: Shot) -> ShotModel:
        query_shot = select(ShotModel).where(
            ShotModel.sequence == self._query_sequence_model(shot.sequence),
            ShotModel.name == shot.name,
            ShotModel.index == shot.index,
        )
        result = self._get_sql_session().execute(query_shot)
        if shot := result.scalar():
            return shot
        else:
            raise ShotNotFoundError(f"Could not find shot {shot} in database")

    def _query_sequence_model(self, sequence: Sequence) -> SequenceModel:
        # noinspection PyProtectedMember
        return self.parent_session.sequence_hierarchy._query_sequence_model(sequence)

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        # noinspection PyProtectedMember
        return self.parent_session._get_sql_session()

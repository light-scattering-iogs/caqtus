import typing

from sqlalchemy import select
from sqlalchemy.orm import Session

from experiment.session import ExperimentSession
from sql_model import ShotModel, DataType

if typing.TYPE_CHECKING:
    from .sequence import Sequence


class Shot:
    def __init__(self, sequence: "Sequence", name: str, index: int):
        self._sequence = sequence
        self._name = name
        self._index = index

    def __str__(self):
        return (
            f'Shot(sequence={self._sequence!s}, name="{self._name}",'
            f" index={self._index})"
        )

    def __repr__(self):
        return (
            f'Shot(sequence={self._sequence!r}, name="{self._name}",'
            f" index={self._index})"
        )

    def get_measures(self, experiment_session: ExperimentSession):
        session = experiment_session.get_sql_session()
        shot_sql = self._query_model(session)
        return shot_sql.get_data(DataType.MEASURE, session)

    def get_parameters(self, experiment_session: ExperimentSession):
        session = experiment_session.get_sql_session()
        shot_sql = self._query_model(session)
        return shot_sql.get_data(DataType.PARAMETER, session)

    @property
    def sequence(self):
        return self._sequence

    @property
    def name(self):
        return self._name

    @property
    def index(self):
        return self._index

    def _query_model(self, session: typing.Optional[Session]) -> ShotModel:
        # noinspection PyProtectedMember
        query_shot = select(ShotModel).where(
            ShotModel.sequence == self.sequence._query_model(session),
            ShotModel.name == self.name,
            ShotModel.index == self.index,
        )
        result = session.execute(query_shot)
        # noinspection PyTypeChecker
        if shot := result.scalar():
            return shot
        else:
            raise ShotNotFoundError(f"Could not find shot {self!s} in database")


class ShotNotFoundError(Exception):
    pass

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker, Session

from experiment_config import ExperimentConfig
from sequence.configuration import SequenceConfig
from .model import SequenceModel
from .path import SequencePath
from .state import State


class Sequence:
    def __init__(self, path: str, session_maker: sessionmaker):
        self._session_maker = session_maker
        self._path = SequencePath(path)

    @property
    def path(self) -> SequencePath:
        return self._path

    def get_creation_date(self, session: Optional[Session] = None) -> datetime:
        if session is None:
            session = self._session

        with session as session:
            sequence_sql = self._query_model(session)
            return sequence_sql.creation_date

    @classmethod
    def create_sequence(
        cls,
        path: str,
        sequence_config: SequenceConfig,
        experiment_config: Optional[ExperimentConfig],
        session_maker: sessionmaker,
    ) -> "Sequence":
        if not isinstance(sequence_config, SequenceConfig):
            raise TypeError(
                f"Type of sequence_config {type(sequence_config)} is not SequenceConfig"
            )

        if experiment_config is not None and not isinstance(
            experiment_config, ExperimentConfig
        ):
            raise TypeError(
                f"Type of experiment_config {type(experiment_config)} is not"
                " ExperimentConfig"
            )

        now = datetime.now()
        creation_args = {
            "path": str(
                SequencePath(path)  # raise ValueError if path has invalid format
            ),
            "state": State.DRAFT,
            "sequence_config_yaml": sequence_config.to_yaml(),
            "experiment_config_yaml": experiment_config.to_yaml()
            if experiment_config
            else None,
            "creation_date": now,
            "modification_date": now,
            "start_date": None,
            "stop_date": None,
        }

        sequence_sql = SequenceModel(**creation_args)
        with session_maker.begin() as session:
            session.add(sequence_sql)
        sequence = cls(path, session_maker)
        return sequence

    @property
    def _session(self):
        return self._session_maker.begin()

    def _query_model(self, session: Optional[Session]) -> SequenceModel:
        stmt = select(SequenceModel).where(SequenceModel.path == str(self._path))
        result = session.execute(stmt)
        # noinspection PyTypeChecker
        if sequence := result.scalar():
            return sequence
        else:
            raise SequenceNotFoundError(f"Could not find sequence '{self._path}' in database")

class SequenceNotFoundError(Exception):
    pass

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from experiment_config import ExperimentConfig
from sequence.configuration import SequenceConfig
from .model import SequenceModel, ShotModel
from .path import SequencePath
from .shot import Shot


class Sequence:
    def __init__(self, path: str):
        self._path = SequencePath(path)

    def __str__(self):
        return f"Sequence(\"{str(self._path)}\")"

    @property
    def path(self) -> SequencePath:
        return self._path

    def get_creation_date(self, session: Session) -> datetime:
        sequence_sql = self.query_model(session)
        return sequence_sql.creation_date

    def get_shots(self, session: Session) -> list[Shot]:
        sequence_sql = self.query_model(session)
        return [Shot(self, shot.name, shot.index) for shot in sequence_sql.shots]

    def create_shot(
        self, name: str, start_time: datetime, end_time: datetime, session: Session
    ) -> Shot:
        shot = ShotModel.create_shot(
            self.query_model(session), name, start_time, end_time, session
        )
        return Shot(self, shot.name, shot.index)

    @classmethod
    def create_sequence(
        cls,
        path: str,
        sequence_config: SequenceConfig,
        experiment_config: Optional[ExperimentConfig],
        session: Session,
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

        SequenceModel.create_sequence(
            SequencePath(path), sequence_config, experiment_config, session
        )
        sequence = cls(path)
        return sequence

    def query_model(self, session: Optional[Session]) -> SequenceModel:
        stmt = select(SequenceModel).where(SequenceModel.path == str(self._path))
        result = session.execute(stmt)
        # noinspection PyTypeChecker
        if sequence := result.scalar():
            return sequence
        else:
            raise SequenceNotFoundError(
                f"Could not find sequence '{self._path}' in database"
            )


class SequenceNotFoundError(Exception):
    pass

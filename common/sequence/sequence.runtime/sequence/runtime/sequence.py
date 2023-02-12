from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from experiment_config import ExperimentConfig
from sequence.configuration import SequenceConfig
from .model import SequenceModel, ShotModel
from .path import SequencePath, PathNotFoundError
from .shot import Shot


class Sequence:
    def __init__(self, path: SequencePath):
        self._path = path

    def __str__(self):
        return f'Sequence("{str(self._path)}")'

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
        path: SequencePath,
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

        path.create(session)
        if path.has_children(session):
            raise RuntimeError(
                f"Cannot create a sequence at {path} because it is a folder with"
                " children"
            )

        SequenceModel.create_sequence(path, sequence_config, experiment_config, session)
        sequence = cls(path)
        return sequence

    def query_model(self, session: Optional[Session]) -> SequenceModel:
        try:
            path = self._path.query_model(session)
        except PathNotFoundError:
            raise SequenceNotFoundError(
                f"Could not find sequence '{self._path}' in database"
            )
        query_sequence = select(SequenceModel).where(SequenceModel.path == path)
        result = session.execute(query_sequence)
        # noinspection PyTypeChecker
        if sequence := result.scalar():
            return sequence
        else:
            raise SequenceNotFoundError(
                f"Could not find sequence '{self._path}' in database"
            )


class SequenceNotFoundError(Exception):
    pass

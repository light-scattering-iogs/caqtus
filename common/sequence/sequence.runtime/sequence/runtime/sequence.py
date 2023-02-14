from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from experiment_config import ExperimentConfig
from sequence.configuration import SequenceConfig, ShotConfiguration
from .model import SequenceModel, ShotModel
from .path import SequencePath, PathNotFoundError
from .shot import Shot
from .state import State


class SequenceNotEditableError(Exception):
    pass


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
        # noinspection PyTypeChecker
        return sequence_sql.creation_date

    def get_config(self, session) -> SequenceConfig:
        yaml = self.query_model(session).sequence_config_yaml
        # noinspection PyTypeChecker
        return SequenceConfig.from_yaml(yaml)

    def set_config(self, config: SequenceConfig, session):
        if not isinstance(config, SequenceConfig):
            raise TypeError(
                f"Expected instance of <SequenceConfig>, got {type(config)}"
            )
        sequence = self.query_model(session)
        if sequence.state != State.DRAFT:
            raise SequenceNotEditableError(f"Sequence is in state {sequence.state}")
        sequence.number_completed_shots = config.compute_total_number_of_shots()
        sequence.sequence_config_yaml = config.to_yaml()
        sequence.modification_date = datetime.now()
        session.flush()

    def set_shot_config(
        self, shot_name: str, shot_config: ShotConfiguration, session: Session
    ):
        if not isinstance(shot_config, ShotConfiguration):
            raise TypeError(
                f"Expected instance of <ShotConfiguration>, got {type(shot_config)}"
            )
        sequence_config = self.get_config(session)
        sequence_config.shot_configurations[shot_name] = shot_config
        self.set_config(sequence_config, session)

    def get_state(self, session) -> State:
        state = self.query_model(session).state
        # noinspection PyTypeChecker
        return state

    def get_shots(self, session: Session) -> list[Shot]:
        sequence_sql = self.query_model(session)
        # noinspection PyTypeChecker
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
            path = self._path._query_model(session)
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

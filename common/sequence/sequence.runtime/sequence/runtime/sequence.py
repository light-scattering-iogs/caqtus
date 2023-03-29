from datetime import datetime
from typing import Optional, Any, TypedDict, Self

from sqlalchemy import select
from sqlalchemy.orm import Session

from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSession
from sequence.configuration import SequenceConfig, ShotConfiguration, SequenceSteps
from sql_model import SequenceModel, ShotModel, State, DataType
from sql_model.sequence_state import InvalidSequenceStateError
from .path import SequencePath, PathNotFoundError
from .shot import Shot


class SequenceNotEditableError(Exception):
    pass


class Sequence:
    def __init__(self, path: SequencePath | str):
        if isinstance(path, SequencePath):
            self._path = path
        elif isinstance(path, str):
            self._path = SequencePath(path)
        else:
            raise TypeError(
                f"Expected instance of <SequencePath> or <str>, got {type(path)}"
            )

    def __str__(self):
        return f'Sequence("{str(self._path)}")'

    @property
    def path(self) -> SequencePath:
        return self._path

    def get_creation_date(self, experiment_session: ExperimentSession) -> datetime:
        sequence_sql = self._query_model(experiment_session.get_sql_session())
        # noinspection PyTypeChecker
        return sequence_sql.creation_date

    def get_config(self, experiment_session: ExperimentSession) -> SequenceConfig:
        yaml = self._query_model(
            experiment_session.get_sql_session()
        ).config.sequence_config_yaml
        # noinspection PyTypeChecker
        return SequenceConfig.from_yaml(yaml)

    def set_config(self, config: SequenceConfig, experiment_session: ExperimentSession):
        if not isinstance(config, SequenceConfig):
            raise TypeError(
                f"Expected instance of <SequenceConfig>, got {type(config)}"
            )

        session = experiment_session.get_sql_session()
        sequence = self._query_model(session)
        if sequence.state != State.DRAFT:
            raise SequenceNotEditableError(f"Sequence is in state {sequence.state}")
        sequence.total_number_shots = config.compute_total_number_of_shots()
        yaml = config.to_yaml()
        assert (
            SequenceConfig.from_yaml(yaml) == config
        )  # will trigger validation before saving
        sequence.config.sequence_config_yaml = yaml
        sequence.modification_date = datetime.now()
        session.flush()

    def set_experiment_config(
        self, experiment_config: str, experiment_session: ExperimentSession
    ):
        if self.get_state(experiment_session) != State.DRAFT:
            raise RuntimeError(
                "Cannot set experiment config for a sequence that is not in draft state"
            )
        session = experiment_session.get_sql_session()
        sequence = self._query_model(session)
        sequence.set_experiment_config(experiment_config)
        session.flush()

    def get_experiment_config(
        self, experiment_session: ExperimentSession
    ) -> Optional[ExperimentConfig]:
        session = experiment_session.get_sql_session()
        sequence = self._query_model(session)

        experience_config_model = sequence.get_experiment_config()
        if experience_config_model is None:
            return None
        return ExperimentConfig.from_yaml(
            experience_config_model.experiment_config_yaml
        )

    def set_shot_config(
        self,
        shot_name: str,
        shot_config: ShotConfiguration,
        experiment_session: ExperimentSession,
    ):
        if not isinstance(shot_config, ShotConfiguration):
            raise TypeError(
                f"Expected instance of <ShotConfiguration>, got {type(shot_config)}"
            )
        sequence_config = self.get_config(experiment_session)
        sequence_config.shot_configurations[shot_name] = shot_config
        self.set_config(sequence_config, experiment_session)

    def set_steps_program(
        self, steps: SequenceSteps, experiment_session: ExperimentSession
    ):
        """Set the steps of the sequence."""

        if not isinstance(steps, SequenceSteps):
            raise TypeError(f"Expected instance of <SequenceSteps>, got {type(steps)}")
        sequence_config = self.get_config(experiment_session)
        sequence_config.program = steps
        self.set_config(sequence_config, experiment_session)

    def get_state(self, experiment_session: ExperimentSession) -> State:
        state = self._query_model(experiment_session.get_sql_session()).state
        # noinspection PyTypeChecker
        return state

    def set_state(self, new_state: State, experiment_session: ExperimentSession):
        session = experiment_session.get_sql_session()
        sequence = self._query_model(session)
        sequence.set_state(new_state)
        session.flush()

    def get_shots(self, experiment_session: ExperimentSession) -> list[Shot]:
        sequence_sql = self._query_model(experiment_session.get_sql_session())
        # noinspection PyTypeChecker
        return [Shot(self, shot.name, shot.index) for shot in sequence_sql.shots][
            : sequence_sql.number_completed_shots
        ]

    def create_shot(
        self,
        name: str,
        start_time: datetime,
        end_time: datetime,
        parameters: dict[str, Any],
        measures: dict[str, Any],
        experiment_session: ExperimentSession,
    ) -> Shot:
        if self.get_state(experiment_session) != State.RUNNING:
            raise InvalidSequenceStateError(
                f"Can't create a shot unless the sequence is running"
            )
        session = experiment_session.get_sql_session()
        sequence = self._query_model(session)
        shot = ShotModel.create_shot(sequence, name, start_time, end_time, session)
        shot.add_data(parameters, DataType.PARAMETER, session)
        shot.add_data(measures, DataType.MEASURE, session)
        sequence.increment_number_completed_shots()
        session.flush()
        return Shot(self, shot.name, shot.index)

    @classmethod
    def create_sequence(
        cls,
        path: SequencePath,
        sequence_config: SequenceConfig,
        experiment_config_name: Optional[str],
        experiment_session: ExperimentSession,
    ) -> "Sequence":
        if not isinstance(sequence_config, SequenceConfig):
            raise TypeError(
                f"Type of sequence_config {type(sequence_config)} is not SequenceConfig"
            )

        path.create(experiment_session)
        if path.has_children(experiment_session):
            raise RuntimeError(
                f"Cannot create a sequence at {path} because it is a folder with"
                " children"
            )

        SequenceModel.create_sequence(
            str(path),
            sequence_config,
            experiment_config_name,
            experiment_session.get_sql_session(),
        )
        sequence = cls(path)
        return sequence

    def _query_model(self, session: Optional[Session]) -> SequenceModel:
        try:
            # noinspection PyProtectedMember
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

    def get_stats(self, experiment_session: ExperimentSession) -> "SequenceStats":
        session = experiment_session.get_sql_session()
        # noinspection PyProtectedMember
        sequence = self._path._query_model(session).get_sequence()
        return SequenceStats(
            state=sequence.get_state(),
            total_number_shots=sequence.total_number_shots,
            number_completed_shots=sequence.get_number_completed_shots(),
            start_date=sequence.start_date,
            stop_date=sequence.stop_date,
        )

    @classmethod
    def query_sequence_stats(
        cls, sequences: list[Self], experiment_session: ExperimentSession
    ) -> dict[SequencePath, "SequenceStats"]:
        session = experiment_session.get_sql_session()
        paths = SequencePath.query_path_models(
            [sequence.path for sequence in sequences], experiment_session
        )
        query = select(SequenceModel).where(
            SequenceModel.path_id.in_(path.id_ for path in paths)
        )
        result = session.execute(query)
        return {
            SequencePath(str(sequence.path)): SequenceStats(
                state=sequence.get_state(),
                total_number_shots=sequence.total_number_shots,
                number_completed_shots=sequence.get_number_completed_shots(),
                start_date=sequence.start_date,
                stop_date=sequence.stop_date,
            )
            for sequence in result.scalars()
        }

    def __eq__(self, other):
        if isinstance(other, Sequence):
            return self.path == other.path
        return False

    def __hash__(self):
        return hash(self.path)


class SequenceStats(TypedDict):
    state: State
    total_number_shots: Optional[int]
    number_completed_shots: int
    start_date: Optional[datetime]
    stop_date: Optional[datetime]


class SequenceNotFoundError(Exception):
    pass

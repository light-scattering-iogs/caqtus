import typing
from datetime import datetime

from data_types import Data, DataLabel
from device.name import DeviceName
from parameter_types import Parameter
from sql_model import DataType
from variable.name import DottedVariableName

if typing.TYPE_CHECKING:
    from experiment.session import ExperimentSession
    from .sequence import Sequence
else:
    ExperimentSession = "ExperimentSession"


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

    def get_measures(
        self, experiment_session: ExperimentSession
    ) -> dict[DeviceName, dict[DataLabel, Data]]:
        return self._get_data(DataType.MEASURE, experiment_session)

    def get_parameters(
        self, experiment_session: ExperimentSession
    ) -> dict[DottedVariableName, Parameter]:
        result = self._get_data(DataType.PARAMETER, experiment_session)
        return {
            DottedVariableName(name): parameter for name, parameter in result.items()
        }

    def get_scores(self, experiment_session: ExperimentSession):
        return self._get_data(DataType.SCORE, experiment_session)

    def _get_data(self, data_type: DataType, experiment_session: ExperimentSession):
        return experiment_session.shot_collection.get_shot_data(
            shot=self, data_type=data_type
        )

    def add_scores(
        self, score: dict[str, float], experiment_session: ExperimentSession
    ):
        experiment_session.shot_collection.add_shot_data(self, score, DataType.SCORE)

    def get_start_time(self, experiment_session: ExperimentSession) -> datetime:
        return experiment_session.shot_collection.get_shot_start_time(self)

    def get_end_time(self, experiment_session: ExperimentSession) -> datetime:
        return experiment_session.shot_collection.get_shot_end_time(self)

    @property
    def sequence(self):
        return self._sequence

    @property
    def name(self):
        return self._name

    @property
    def index(self):
        return self._index

    def __eq__(self, other):
        return (
            isinstance(other, Shot)
            and self.sequence == other.sequence
            and self.name == other.name
            and self.index == other.index
        )

    def __hash__(self):
        return hash((self.sequence, self.name, self.index))


class ShotNotFoundError(Exception):
    pass

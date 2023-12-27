from __future__ import annotations

import typing
from collections.abc import Mapping
from datetime import datetime

from core.types import Parameter, Data, DataLabel
from device.name import DeviceName
from variable.name import DottedVariableName
from ..data_type import DataType

# We don't do these imports at runtime because it would create a circular import.
if typing.TYPE_CHECKING:
    from .sequence import Sequence
    from ..experiment_session import ExperimentSession


class Shot:
    """Gives access to the data of a shot.

    All methods of this class take an :py:class:`ExperimentSession` argument in witch to look for the shot.
    It is not recommended to create :py:class:`Shot` objects directly. Instead, consider using the method
    :py:meth:`Sequence.get_shots`.
    """

    def __init__(self, sequence: Sequence, name: str, index: int):
        self._sequence = sequence
        self._name = name
        self._index = index

    @property
    def sequence(self):
        """The sequence to which this shot belongs."""

        return self._sequence

    @property
    def name(self):
        """The name of this shot."""

        return self._name

    @property
    def index(self):
        """The index of this shot in the sequence.

        Shots are indexed from 0 to N-1 in the order in which they were scheduled, not necessarily in the order in which
        they were run.
        """

        return self._index

    def get_measures(
        self, experiment_session: ExperimentSession
    ) -> Mapping[DeviceName, Mapping[DataLabel, Data]]:
        """Returns all data that were acquired during this shot."""

        return self._get_data_by_type(DataType.MEASURE, experiment_session)

    def get_parameters(
        self, experiment_session: ExperimentSession
    ) -> Mapping[DottedVariableName, Parameter]:
        """Returns the values of the parameters used to run this shot."""

        result = self._get_data_by_type(DataType.PARAMETER, experiment_session)
        return {
            DottedVariableName(name): parameter for name, parameter in result.items()
        }

    def get_start_time(self, experiment_session: ExperimentSession) -> datetime:
        """Returns the time at which the shot started to run on the experiment."""

        return experiment_session.shot_collection.get_shot_start_time(self)

    def get_end_time(self, experiment_session: ExperimentSession) -> datetime:
        """Returns the time at which the shot finished running on the experiment."""

        return experiment_session.shot_collection.get_shot_end_time(self)

    def get_data_by_label(
        self, data_label: str, experiment_session: ExperimentSession
    ) -> Data:
        """Returns the data associated with the given label."""

        return experiment_session.shot_collection.get_shot_data(
            shot=self, data_label=data_label
        )

    def get_scores(self, experiment_session: ExperimentSession) -> Mapping[str, float]:
        """Returns the scores associated with this shot.

        A score is a value that can be set by the user to evaluate the quality of the shot after it's been run.
        """

        return self._get_data_by_type(DataType.SCORE, experiment_session)

    def add_scores(
        self, score: Mapping[str, float], experiment_session: ExperimentSession
    ) -> None:
        """Set some scores for this shot.

        This function takes a mapping as argument such that several scores can be set at once for different metrics.
        """

        experiment_session.shot_collection.add_shot_data(
            self, dict(score), DataType.SCORE
        )

    def _get_data_by_type(
        self, data_type: DataType, experiment_session: ExperimentSession
    ):
        return experiment_session.shot_collection.get_all_shot_data(
            shot=self, data_type=data_type
        )

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

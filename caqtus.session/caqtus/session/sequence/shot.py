from __future__ import annotations

import datetime
import typing
from collections.abc import Mapping

from caqtus.types.data import DataLabel, Data
from caqtus.types.parameter import Parameter
from caqtus.types.variable_name import DottedVariableName

# We don't do these imports at runtime because it would create a circular import.
if typing.TYPE_CHECKING:
    from .sequence import Sequence
    from ..experiment_session import ExperimentSession


class Shot:
    """Gives access to the data of a shot."""

    def __init__(self, sequence: Sequence, index: int):
        self._sequence = sequence
        self._index = index

    @property
    def sequence(self) -> "Sequence":
        """The sequence to which this shot belongs."""

        return self._sequence

    @property
    def index(self) -> int:
        """The index of this shot in the sequence."""

        return self._index

    def __repr__(self):
        return f"Shot(sequence={self._sequence!r}, index={self._index})"

    def __eq__(self, other):
        return (
                isinstance(other, Shot)
                and self.sequence == other.sequence
                and self.index == other.index
        )

    def __hash__(self):
        return hash((self.sequence, self.index))

    def get_parameters(
            self, session: ExperimentSession
    ) -> Mapping[DottedVariableName, Parameter]:
        """Return the parameters used to run this shot."""

        return session.sequences.get_shot_parameters(self.sequence.path, self.index)

    def get_data(self, session: ExperimentSession) -> Mapping[DataLabel, Data]:
        """Return the data of this shot.

        This will return all data that was acquired during the shot.
        If you want to get only a subset of the data, use :meth:`get_data_by_label`
        which will avoid querying unnecessary data.
        """

        return session.sequences.get_all_shot_data(self.sequence.path, self.index)

    def get_data_by_label(self, label: DataLabel, session: ExperimentSession) -> Data:
        """Return the data of this shot with the given label."""

        return session.sequences.get_shot_data_by_label(
            self.sequence.path, self.index, label
        )

    def get_start_time(self, session: ExperimentSession) -> datetime.datetime:
        """Return the time at which this shot started running."""

        return session.sequences.get_shot_start_time(self.sequence.path, self.index)

    def get_end_time(self, session: ExperimentSession) -> datetime.datetime:
        """Return the time at which this shot finished running."""

        return session.sequences.get_shot_end_time(self.sequence.path, self.index)

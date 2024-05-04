from __future__ import annotations

import datetime
import typing
from collections.abc import Mapping

import attrs

from caqtus.types.data import DataLabel, Data
from caqtus.types.parameter import Parameter
from caqtus.types.variable_name import DottedVariableName
from ..path import PureSequencePath
from ..sequence_collection import PureShot

# We don't do these imports at runtime because it would create a circular import.
if typing.TYPE_CHECKING:
    from .sequence import Sequence
    from ..experiment_session import ExperimentSession


@attrs.frozen(eq=False, order=False)
class Shot:
    """Gives access to the data of a shot."""

    sequence_path: PureSequencePath
    index: int
    _session: ExperimentSession

    @classmethod
    def bound(cls, shot: PureShot, session: ExperimentSession) -> typing.Self:
        return cls(shot.sequence_path, shot.index, session)

    @property
    def sequence(self) -> "Sequence":
        """The sequence to which this shot belongs."""

        from .sequence import Sequence

        return Sequence(self.sequence_path, self._session)

    def get_parameters(self) -> Mapping[DottedVariableName, Parameter]:
        """Return the parameters used to run this shot."""

        return self._session.sequences.get_shot_parameters(
            self.sequence_path, self.index
        )

    def get_data(self) -> Mapping[DataLabel, Data]:
        """Return the data of this shot.

        This will return all data that was acquired during the shot.
        If you want to get only a subset of the data, use :meth:`get_data_by_label`
        which will avoid querying unnecessary data.
        """

        return self._session.sequences.get_all_shot_data(self.sequence_path, self.index)

    def get_data_by_label(self, label: DataLabel) -> Data:
        """Return the data of this shot with the given label."""

        return self._session.sequences.get_shot_data_by_label(
            self.sequence_path, self.index, label
        )

    def get_start_time(self) -> datetime.datetime:
        """Return the time at which this shot started running."""

        return self._session.sequences.get_shot_start_time(
            self.sequence_path, self.index
        )

    def get_end_time(self) -> datetime.datetime:
        """Return the time at which this shot finished running."""

        return self._session.sequences.get_shot_end_time(self.sequence_path, self.index)

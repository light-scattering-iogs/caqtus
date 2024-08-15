from __future__ import annotations

import datetime
import typing
from collections.abc import Mapping, Set

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
    """Represents a shot inside a sequence."""

    sequence_path: PureSequencePath
    index: int
    _session: ExperimentSession

    # Since the session implements repeatable reads, we can cache the data that we have
    # already fetched and know that they are up-to-date.
    # Warning: This only works if the current session does not update the shot, which
    # should not happen on the user side.
    _data_cache: dict[DataLabel, Data] = attrs.field(factory=dict)

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

        data = self._session.sequences.get_all_shot_data(self.sequence_path, self.index)
        self._data_cache.update(data)
        return data

    def get_data_by_label(self, label: DataLabel) -> Data:
        """Return the data of this shot with the given label."""

        if label in self._data_cache:
            return self._data_cache[label]
        else:
            data = self._session.sequences.get_shot_data_by_label(
                self.sequence_path, self.index, label
            )
            self._data_cache[label] = data
            return data

    def get_data_by_labels(self, labels: Set[DataLabel]) -> Mapping[DataLabel, Data]:
        """Return the data of this shot with the given labels."""

        cached = set(self._data_cache.keys())
        to_fetch = labels - cached

        fetched = self._session.sequences.get_shot_data_by_labels(
            self.sequence_path, self.index, to_fetch
        )
        self._data_cache.update(fetched)

        return {label: self._data_cache[label] for label in labels}

    def get_start_time(self) -> datetime.datetime:
        """Return the time at which this shot started running."""

        return self._session.sequences.get_shot_start_time(
            self.sequence_path, self.index
        )

    def get_end_time(self) -> datetime.datetime:
        """Return the time at which this shot finished running."""

        return self._session.sequences.get_shot_end_time(self.sequence_path, self.index)

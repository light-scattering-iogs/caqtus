from __future__ import annotations

import abc
import datetime
from collections.abc import Mapping
from typing import Protocol, Optional

import attrs
from caqtus.device import DeviceName, DeviceConfigurationAttrs
from caqtus.types.data import DataLabel, Data
from caqtus.types.parameter import Parameter
from caqtus.types.variable_name import DottedVariableName
from returns.result import Result

from .parameter_namespace import ParameterNamespace
from .path import PureSequencePath
from .path_hierarchy import PathError, PathNotFoundError
from .sequence import Sequence, Shot
from .sequence.iteration_configuration import IterationConfiguration
from .sequence.state import State
from .shot import TimeLanes


class PathIsSequenceError(PathError):
    pass


class PathIsNotSequenceError(PathError):
    pass


class SequenceStateError(RuntimeError):
    """Raised when an invalid sequence state is encountered.

    This error is raised when trying to perform an operation that is not allowed in the
    current state, such as adding data to a sequence that is not in the RUNNING state.
    """

    pass


class InvalidStateTransitionError(SequenceStateError):
    """Raised when an invalid state transition is attempted.

    This error is raised when trying to transition a sequence to an invalid state.
    """

    pass


class SequenceNotEditableError(SequenceStateError):
    pass


class ShotNotFoundError(RuntimeError):
    pass


class SequenceCollection(Protocol):
    """A collection of sequences.

    This abstract class defines the interface to read and write sequences in a session.
    Objects of this class provide methods for full access to read/write operations on
    sequences and their shots.
    However, they are not meant to be convenient to use directly in user code.
    Instead, consider using the higher-level API provided by the
    :class:`caqtus.session.Sequence` and :class:`caqtus.session.Shot` classes to access data
    from sequences and shots.
    """

    @abc.abstractmethod
    def __getitem__(self, item: str) -> Sequence:
        raise NotImplementedError

    @abc.abstractmethod
    def is_sequence(self, path: PureSequencePath) -> Result[bool, PathNotFoundError]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_contained_sequences(self, path: PureSequencePath) -> list[PureSequencePath]:
        """Return the children of this path that are sequences, including this path.

        Return:
            A list of all sequences inside this path and all its descendants.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def set_global_parameters(
        self, path: PureSequencePath, parameters: ParameterNamespace
    ) -> None:
        """Set the global parameters that should be used by this sequence.

        Raises:
            SequenceNotEditable: If the sequence is not in the PREPARING state.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_global_parameters(self, path: PureSequencePath) -> ParameterNamespace:
        """Get the global parameters that were used by this sequence.

        Raises:
            RuntimeError: If the sequence has not been prepared yet.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_iteration_configuration(
        self, sequence: PureSequencePath
    ) -> IterationConfiguration:
        """Return a copy of the iteration configuration for this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def set_iteration_configuration(
        self, sequence: Sequence, iteration_configuration: IterationConfiguration
    ) -> None:
        """Set the iteration configuration for this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def get_time_lanes(self, sequence_path: PureSequencePath) -> TimeLanes:
        """Return a copy of the time lanes for this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def set_time_lanes(
        self, sequence_path: PureSequencePath, time_lanes: TimeLanes
    ) -> None:
        """Set the time lanes that define how a shot is run for this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def set_device_configurations(
        self,
        path: PureSequencePath,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    ) -> None:
        """Set the device configurations that should be used by this sequence.

        Raises:
            SequenceNotEditableError: If the sequence is not in the PREPARING state.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_device_configurations(
        self, path: PureSequencePath
    ) -> Mapping[DeviceName, DeviceConfigurationAttrs]:
        """Get the device configurations that are used by this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def create(
        self,
        path: PureSequencePath,
        iteration_configuration: IterationConfiguration,
        time_lanes: TimeLanes,
    ) -> Sequence:
        """Create a new sequence at the given path.

        Raises:
            PathIsSequenceError: If the path already exists and is a sequence.
            PathHasChildrenError: If the path already exists and has children.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_state(
        self, path: PureSequencePath
    ) -> Result[State, PathNotFoundError | PathIsNotSequenceError]:
        raise NotImplementedError

    @abc.abstractmethod
    def set_state(self, path: PureSequencePath, state: State) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_stats(
        self, path: PureSequencePath
    ) -> Result[SequenceStats, PathNotFoundError | PathIsNotSequenceError]:
        raise NotImplementedError

    @abc.abstractmethod
    def create_shot(
        self,
        path: PureSequencePath,
        shot_index: int,
        shot_parameters: Mapping[DottedVariableName, Parameter],
        shot_data: Mapping[DataLabel, Data],
        shot_start_time: datetime.datetime,
        shot_end_time: datetime.datetime,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_shots(
        self, path: PureSequencePath
    ) -> Result[list[Shot], PathNotFoundError | PathIsNotSequenceError]:
        """Return the shots that belong to this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def get_shot_parameters(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DottedVariableName, Parameter]:
        """Return the shots that belong to this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def get_all_shot_data(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DataLabel, Data]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_shot_data_by_label(
        self, path: PureSequencePath, shot_index: int, data_label: DataLabel
    ) -> Data:
        raise NotImplementedError

    @abc.abstractmethod
    def get_shot_start_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime.datetime:
        raise NotImplementedError

    @abc.abstractmethod
    def get_shot_end_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime.datetime:
        raise NotImplementedError

    @abc.abstractmethod
    def update_start_and_end_time(
        self,
        path: PureSequencePath,
        start_time: Optional[datetime.datetime],
        end_time: Optional[datetime.datetime],
    ) -> None:
        """Update the start and end time of the sequence.

        This method is used for maintenance purposes, such as when copying a sequence from one session to another.
        It should not be used to record the start and end time of a sequence during normal operation.
        """

        raise NotImplementedError


@attrs.frozen
class SequenceStats:
    state: State
    start_time: Optional[datetime.datetime]
    stop_time: Optional[datetime.datetime]
    number_completed_shots: int
    expected_number_shots: Optional[int]

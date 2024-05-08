from __future__ import annotations

import abc
import datetime
from collections.abc import Mapping, Set
from typing import Protocol, Optional

import attrs
from returns.result import Result

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.types.data import DataLabel, Data
from caqtus.types.parameter import Parameter
from caqtus.types.timelane import TimeLanes
from caqtus.types.variable_name import DottedVariableName
from .parameter_namespace import ParameterNamespace
from .path import PureSequencePath
from .path_hierarchy import PathError, PathNotFoundError
from .sequence.iteration_configuration import IterationConfiguration, Unknown
from .sequence.state import State


class PathIsSequenceError(PathError):
    pass


class PathIsNotSequenceError(PathError):
    pass

class DataNotFoundError(RuntimeError):
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
    :class:`caqtus.session.Sequence` and :class:`caqtus.session.Shot` classes to access
    data from sequences and shots.
    """

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
            RuntimeError: If the sequence is in draft mode, since the global parameters
            are only set once the sequence has entered the PREPARING state.
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
        self,
        sequence: PureSequencePath,
        iteration_configuration: IterationConfiguration,
    ) -> None:
        """Set the iteration configuration for this sequence.

        Raises:
            PathNotFoundError: If the path doesn't exist.
            PathIsNotSequenceError: If the path is not a sequence.
            SequenceNotEditableError: If the sequence is not in DRAFT state.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_time_lanes(self, sequence_path: PureSequencePath) -> TimeLanes:
        """Return a copy of the time lanes for this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def set_time_lanes(
        self, sequence_path: PureSequencePath, time_lanes: TimeLanes
    ) -> None:
        """Set the time lanes that define how a shot is run for this sequence.

        Raises:
            PathNotFoundError: If the path doesn't exist.
            PathIsNotSequenceError: If the path is not a sequence.
            SequenceNotEditableError: If the sequence is not in DRAFT state.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def set_device_configurations(
        self,
        path: PureSequencePath,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
    ) -> None:
        """Set the device configurations that should be used by this sequence.

        Raises:
            SequenceNotEditableError: If the sequence is not in the PREPARING state.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_device_configurations(
        self, path: PureSequencePath
    ) -> Mapping[DeviceName, DeviceConfiguration]:
        """Get the device configurations that are used by this sequence.

        Raises:
            RuntimeError: If the sequence is in draft mode, since the device
            configurations are only set once the sequence has entered the PREPARING
            state.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def create(
        self,
        path: PureSequencePath,
        iteration_configuration: IterationConfiguration,
        time_lanes: TimeLanes,
    ) -> None:
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
    ) -> Result[list[PureShot], PathNotFoundError | PathIsNotSequenceError]:
        """Return the shots that belong to this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def get_shot_parameters(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DottedVariableName, Parameter]:

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
        """Return the data with the given label for the shot at the given index.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
            PathIsNotSequenceError: If the path is not a sequence.
            ShotNotFoundError: If the shot does not exist in the sequence.
            DataNotFoundError: If the data with the given label does not exist in the
            shot.
        """

        raise NotImplementedError


    def get_shot_data_by_labels(self, path: PureSequencePath, shot_index: int, data_labels: Set[DataLabel]) -> Mapping[DataLabel, Data]:
        """Return the data with the given labels for the shot at the given index.

        This method is equivalent to calling :meth:`get_shot_data_by_label` for each
        label in the set, but can be faster.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
            PathIsNotSequenceError: If the path is not a sequence.
            ShotNotFoundError: If the shot does not exist in the sequence.
            DataNotFoundError: If one of the data labels does not exist in the shot.
        """

        # Naive implementation that calls get_shot_data_by_label for each label.
        return {
            label: self.get_shot_data_by_label(path, shot_index, label)
            for label in data_labels
        }

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

        This method is used for maintenance purposes, such as when copying a sequence
        from one session to another.
        It should not be used to record the start and end time of a sequence during
        normal operation.
        """

        raise NotImplementedError


@attrs.frozen
class SequenceStats:
    state: State
    start_time: Optional[datetime.datetime]
    stop_time: Optional[datetime.datetime]
    number_completed_shots: int
    expected_number_shots: int | Unknown


@attrs.frozen
class PureShot:
    """Unique identifier for a shot in a sequence."""

    sequence_path: PureSequencePath
    index: int

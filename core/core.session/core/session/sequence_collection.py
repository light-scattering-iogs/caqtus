from __future__ import annotations

import abc
import datetime
from collections.abc import Mapping
from typing import Protocol, Optional, TypeAlias

import attrs
from returns.result import Result

from core.device import DeviceName, DeviceConfigurationAttrs
from core.types.data import DataLabel, Data
from core.types.parameter import Parameter
from core.types.variable_name import DottedVariableName
from .path import PureSequencePath
from .path_hierarchy import PathError, PathNotFoundError
from .sequence import Sequence, Shot
from .sequence.iteration_configuration import (
    IterationConfiguration,
    VariableDeclaration,
)
from .sequence.state import State
from .shot import TimeLanes

ConstantTable: TypeAlias = list[VariableDeclaration]


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
            SequenceNotEditableError: If the sequence is not in an editable state.
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
    def set_parameter_tables(
        self, path: PureSequencePath, parameter_tables: Mapping[str, ConstantTable]
    ) -> None:
        """Set the parameter tables that are used by this sequence."""

        raise NotImplementedError

    @abc.abstractmethod
    def get_parameter_tables(
        self, path: PureSequencePath
    ) -> Mapping[str, ConstantTable]:
        """Get the parameter tables that are used by this sequence."""

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
    def get_shots(self, path: PureSequencePath) -> list[Shot]:
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


@attrs.frozen
class SequenceStats:
    state: State
    start_time: Optional[datetime.datetime]
    stop_time: Optional[datetime.datetime]
    number_completed_shots: int
    expected_number_shots: Optional[int]

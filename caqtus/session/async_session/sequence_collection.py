import abc
import datetime
from collections.abc import Mapping
from typing import Protocol, Optional

from caqtus.types.data import DataLabel, Data
from caqtus.types.iteration import IterationConfiguration
from caqtus.types.parameter import Parameter, ParameterNamespace
from caqtus.types.timelane import TimeLanes
from caqtus.types.variable_name import DottedVariableName
from .._exception_summary import TracebackSummary
from .._result import Result
from .._path import PureSequencePath
from .._path_hierarchy import PathNotFoundError
from .._sequence_collection import (
    PathIsNotSequenceError,
    SequenceStats,
    PureShot,
    SequenceNotCrashedError,
)
from .._state import State


class AsyncSequenceCollection(Protocol):
    @abc.abstractmethod
    async def is_sequence(
        self, path: PureSequencePath
    ) -> Result[bool, PathNotFoundError]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_stats(
        self, path: PureSequencePath
    ) -> Result[SequenceStats, PathNotFoundError | PathIsNotSequenceError]:
        raise NotImplementedError

    async def get_state(
        self, path: PureSequencePath
    ) -> Result[State, PathNotFoundError | PathIsNotSequenceError]:

        return (await self.get_stats(path)).map(lambda stats: stats.state)

    @abc.abstractmethod
    async def get_traceback_summary(self, path: PureSequencePath) -> Result[
        Optional[TracebackSummary],
        PathNotFoundError | PathIsNotSequenceError | SequenceNotCrashedError,
    ]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_iteration_configuration(
        self, path: PureSequencePath
    ) -> IterationConfiguration:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_time_lanes(self, path: PureSequencePath) -> TimeLanes:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_global_parameters(self, path: PureSequencePath) -> ParameterNamespace:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_shots(
        self, path: PureSequencePath
    ) -> Result[list[PureShot], PathNotFoundError | PathIsNotSequenceError]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_shot_parameters(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DottedVariableName, Parameter]:

        raise NotImplementedError

    @abc.abstractmethod
    async def get_all_shot_data(
        self, path: PureSequencePath, shot_index: int
    ) -> Mapping[DataLabel, Data]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_shot_data_by_label(
        self, path: PureSequencePath, shot_index: int, data_label: DataLabel
    ) -> Data:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_shot_start_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime.datetime:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_shot_end_time(
        self, path: PureSequencePath, shot_index: int
    ) -> datetime.datetime:
        raise NotImplementedError

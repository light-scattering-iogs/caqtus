import abc
from typing import Protocol

from returns.result import Result

from .. import ParameterNamespace
from ..path import PureSequencePath
from ..path_hierarchy import PathNotFoundError
from ..sequence import State
from ..sequence.iteration_configuration import IterationConfiguration
from ..sequence_collection import PathIsNotSequenceError, SequenceStats
from ..shot import TimeLanes


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

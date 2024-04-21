import abc
from typing import Protocol

from returns.result import Result

from ..path import PureSequencePath
from ..path_hierarchy import PathNotFoundError
from ..sequence_collection import PathIsNotSequenceError, SequenceStats


class AsyncSequenceCollection(Protocol):
    @abc.abstractmethod
    async def get_stats(
        self, path: PureSequencePath
    ) -> Result[SequenceStats, PathNotFoundError | PathIsNotSequenceError]:
        raise NotImplementedError

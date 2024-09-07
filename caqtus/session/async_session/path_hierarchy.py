from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Protocol, TYPE_CHECKING

from .._result import Result
from .._path import PureSequencePath
from .._path_hierarchy import PathNotFoundError, PathIsRootError

if TYPE_CHECKING:
    from .._sequence_collection import PathIsSequenceError


class AsyncPathHierarchy(Protocol):
    @abstractmethod
    async def does_path_exists(self, path: PureSequencePath) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_children(
        self, path: PureSequencePath
    ) -> Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
        raise NotImplementedError

    @abstractmethod
    async def get_path_creation_date(
        self, path: PureSequencePath
    ) -> Result[datetime, PathNotFoundError | PathIsRootError]:
        raise NotImplementedError

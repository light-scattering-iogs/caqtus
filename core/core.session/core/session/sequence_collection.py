import abc
from typing import Protocol
from .path import BoundSequencePath, PathNotFoundError
from returns.result import Result


class SequenceCollection(Protocol):
    @abc.abstractmethod
    def is_sequence(self, path: BoundSequencePath) -> Result[bool, PathNotFoundError]:
        raise NotImplementedError

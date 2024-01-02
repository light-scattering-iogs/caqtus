import abc
from typing import Protocol

from returns.result import Result

from .path import PathNotFoundError, PureSequencePath
from .sequence import Sequence


class SequenceCollection(Protocol):
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
    def create(self, path: PureSequencePath) -> Sequence:
        raise NotImplementedError

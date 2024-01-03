import abc
from typing import Protocol

from returns.result import Result

from .path import PureSequencePath
from .sequence import Sequence
from .path_hierarchy import PathError, PathNotFoundError
from .sequence.iteration_configuration import IterationConfiguration


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
    def get_iteration_configuration(self, sequence: Sequence) -> IterationConfiguration:
        raise NotImplementedError

    @abc.abstractmethod
    def set_iteration_configuration(
        self, sequence: Sequence, iteration_configuration: IterationConfiguration
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def create(
        self, path: PureSequencePath, iteration_configuration: IterationConfiguration
    ) -> Sequence:
        raise NotImplementedError


class PathIsSequenceError(PathError):
    pass


class PathIsNotSequenceError(PathError):
    pass

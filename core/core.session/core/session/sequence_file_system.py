from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Protocol

from returns.result import Result

from .path import PureSequencePath, PathNotFoundError


class SequenceHierarchy(Protocol):
    """Interface that defines the sequence hierarchy of an experiment session.

    This object provides a file-system-like methods that can be used to create, delete
    and check for the existence of sequences.
    """

    @abstractmethod
    def does_path_exists(self, path: PureSequencePath) -> bool:
        """Check if the path exists in the session.

        Args:
            path: the path to check for existence.

        Returns:
            True if the path exists in the session. False otherwise.
        """

        raise NotImplementedError

    @abstractmethod
    def create_path(
        self, path: PureSequencePath
    ) -> Result[list[PureSequencePath], PathIsSequenceError]:
        """Create the path in the session and its parent paths if they do not exist.

        Args:
            path: the path to create.

        Returns:
            A list of the paths that were created if the path was created successfully
            or PathIsSequenceError if the path or one of its ancestors is a sequence.
            No path is created if any of the ancestors is a sequence.
        """

        raise NotImplementedError

    @abstractmethod
    def delete_path(self, path: PureSequencePath, delete_sequences: bool = False):
        """Delete the path and all its descendants.

        Warnings:
            If delete_sequences is True, all sequences in the path will be deleted.

        Args:
            path: The path to delete. Descendants will be deleted recursively.
            delete_sequences: If False, raise an error if the path or one of its
            children is a sequence.

        Raises:
            PathNotFoundError: If the path does not exist.
            PathIsSequenceError: If the path or one of its children is a sequence and
            delete_sequence is False.
        """

        raise NotImplementedError

    @abstractmethod
    def get_children(
        self, path: PureSequencePath
    ) -> Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
        """Get the children of the path."""

        raise NotImplementedError

    @abstractmethod
    def get_path_creation_date(
        self, path: PureSequencePath
    ) -> Result[datetime, PathNotFoundError]:
        """Get the creation date of the path.

        Args:
            path: the path to get the creation date for.

        Returns:
            The creation date of the path.
        """

        raise NotImplementedError

    @abstractmethod
    def get_all_paths(self) -> set[PureSequencePath]:
        """Get all the paths in the session.

        Returns:
            A set of all the paths in the session.
        """

        raise NotImplementedError


class PathIsSequenceError(RuntimeError):
    pass


class PathIsNotSequenceError(RuntimeError):
    pass

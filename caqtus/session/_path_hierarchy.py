from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from typing import Protocol, TYPE_CHECKING

from ._light_result import _Result
from ._path import PureSequencePath

if TYPE_CHECKING:
    from ._sequence_collection import PathIsSequenceError


class PathHierarchy(Protocol):
    """A file-system-like object that exists inside a session.

    This object provides methods that can be used to create, delete and check for the
    existence of sequences.
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
    ) -> _Result[list[PureSequencePath], PathIsSequenceError]:
        """Create the path in the session and its parent paths if they do not exist.

        If is safe to call this methode even if the path already exists, in which case
        it will return a Success with an empty list.

        Args:
            path: the path to create.

        Returns:
            * Success, with a list of the paths that were created if the path was
              created successfully. The list is ordered from parent to child.
            * Failure, with PathIsSequenceError if the path or one of its ancestors is a
              sequence. No path is created if any of the ancestors is a sequence.
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
    ) -> _Result[set[PureSequencePath], PathNotFoundError | PathIsSequenceError]:
        """Get the children of the path."""

        raise NotImplementedError

    @abstractmethod
    def get_path_creation_date(
        self, path: PureSequencePath
    ) -> _Result[datetime, PathNotFoundError | PathIsRootError]:
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

    @abstractmethod
    def update_creation_date(self, path: PureSequencePath, date: datetime) -> None:
        """Update the creation date of the path.

        This method is meant to be used for maintenance purposes only, such as when
        copying sequences from one session to another.

        Args:
            path: the path to update the creation date for.
            date: the new creation date.
        """

        raise NotImplementedError


class PathError(RuntimeError):
    """Base class for all path errors."""

    pass


class PathNotFoundError(PathError):
    """Raised when a path is not found in the session."""

    pass


class PathIsRootError(PathError):
    """Raised when an invalid operation is performed on the root path."""

    pass


class PathHasChildrenError(PathError):
    """Raised when an invalid operation is performed on a path that has children."""

    pass


class PathExistsError(PathError):
    """Raised when a path already exists in the session."""

    pass

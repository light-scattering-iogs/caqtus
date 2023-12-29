from __future__ import annotations

import datetime
import re
from typing import Self, Optional, TYPE_CHECKING, Iterable

from ._return_or_raise import unwrap

if TYPE_CHECKING:
    from .experiment_session import ExperimentSession

_PATH_SEPARATOR = "\\"
_CHARACTER_SET = (
    "["
    "\\w\\d"
    "\\_\\.\\,\\;\\*\\'\\\"\\`"
    "\\(\\)\\[\\]\\{\\}"
    "\\+\\-\\*\\/\\="
    "\\!\\@\\#\\$\\%\\^\\&\\~\\<\\>\\?\\|"
    "]"
)
_PATH_NAME = f"{_CHARACTER_SET}+(?:{_CHARACTER_SET}| )*"
_PATH_NAME_REGEX = re.compile(f"^{_PATH_NAME}$")
_PATH_REGEX = re.compile(f"^\\{_PATH_SEPARATOR}|(\\{_PATH_SEPARATOR}{_PATH_NAME})+$")


class PureSequencePath:
    """A path in the sequence hierarchy.

    A path is a string of names separated by backslashes "\"
    For example, "\foo\bar" is a path with two names, "foo" and "bar".
    The root path is the single backslash "\".
    """

    def __init__(self, path: Self | str):
        if isinstance(path, str):
            self._parts = self.convert_to_parts(path)
            self._str = path
        elif isinstance(path, type(self)):
            self._parts = path.parts
            self._str = path._str
        else:
            raise TypeError(f"Invalid type for path: {type(path)}")

    @property
    def parts(self) -> tuple[str, ...]:
        return self._parts

    @property
    def parent(self) -> Optional[Self]:
        if self.is_root():
            return None
        else:
            return type(self).from_parts(self._parts[:-1])

    @property
    def name(self) -> Optional[str]:
        if self.is_root():
            return None
        else:
            return self._parts[-1]

    @classmethod
    def is_valid_path(cls, path: str) -> bool:
        return bool(_PATH_REGEX.match(path))

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        return bool(_PATH_NAME_REGEX.match(name))

    @classmethod
    def convert_to_parts(cls, path: str) -> tuple[str, ...]:
        if cls.is_valid_path(path):
            if path == _PATH_SEPARATOR:
                return tuple()
            else:
                return tuple(path.split(_PATH_SEPARATOR)[1:])
        else:
            raise ValueError(f"Invalid path: {path}")

    @classmethod
    def from_parts(cls, parts: Iterable[str]) -> Self:
        return cls(_PATH_SEPARATOR + _PATH_SEPARATOR.join(parts))

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._str!r})"

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self._str == other._str
        else:
            return NotImplemented

    def is_root(self) -> bool:
        return len(self._parts) == 0

    def __truediv__(self, other) -> Self:
        if isinstance(other, str):
            if not re.match(_PATH_NAME, other):
                raise ValueError("Invalid name format")
            if self.is_root():
                return type(self)(f"{self._str}{other}")
            else:
                return type(self)(f"{self._str}{_PATH_SEPARATOR}{other}")
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self._str)


class SequencePath(PureSequencePath):
    def exists(self, experiment_session: "ExperimentSession") -> bool:
        return experiment_session.sequence_hierarchy.does_path_exists(self)

    def create(self, experiment_session: "ExperimentSession") -> list[SequencePath]:
        """Create the path and all its ancestors if they don't exist.

        Return:
            A list of paths that were created if they didn't exist.

        Raises:
            PathIsSequenceError: If an ancestor exists and is a sequence.
        """

        result = experiment_session.sequence_hierarchy.create_path(self)
        return unwrap(result)

    def delete(
        self, experiment_session: "ExperimentSession", delete_sequences: bool = False
    ):
        """Delete the path and all its children if they exist.

        Warnings:
            If delete_sequences is True, all sequences in the path will be deleted.

        Raises:
            PathIsSequenceError: If the path or one of its children is a sequence and
            delete_sequence is False
        """

        experiment_session.sequence_hierarchy.delete_path(self, delete_sequences)

    def get_contained_sequences(
        self, experiment_session: "ExperimentSession"
    ) -> list[SequencePath]:
        """Return the children of this path that are sequences, including this path.

        Return:
            A list of all sequences inside this path and all its descendants.
        """

        if self.is_sequence(experiment_session):
            return [self]

        result = []
        for child in self.get_children(experiment_session):
            result += child.get_contained_sequences(experiment_session)
        return result

    def is_folder(self, experiment_session: "ExperimentSession") -> bool:
        """Check if the path is a folder.

        Returns:
            True if the path is a folder path. False otherwise.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
        """

        return not self.is_sequence(experiment_session)

    def is_sequence(self, experiment_session: "ExperimentSession") -> bool:
        """Check if the path is a sequence.

        Returns:
            True if the path is a sequence path. False otherwise.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
        """

        result = experiment_session.sequence_hierarchy.is_sequence_path(self)

        return unwrap(result)

    def has_children(self, experiment_session: "ExperimentSession") -> int:
        return bool(self.get_child_count(experiment_session))

    def get_child_count(self, experiment_session: "ExperimentSession") -> int:
        return len(self.get_children(experiment_session))

    def get_children(
        self, experiment_session: "ExperimentSession"
    ) -> set[SequencePath]:
        """Return the direct descendants of this path.

        Returns:
            A set of the direct descendants of this path.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
            PathIsSequenceError: If the path is a sequence.
        """

        result = experiment_session.sequence_hierarchy.get_path_children(self)
        return unwrap(result)

    def get_creation_date(
        self, experiment_session: "ExperimentSession"
    ) -> datetime.datetime:
        """Get the creation date of the path.

        Returns:
            The date at which the path was created.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
        """

        result = experiment_session.sequence_hierarchy.get_path_creation_date(self)
        return unwrap(result)

    def get_ancestors(self, strict: bool = True) -> list[SequencePath]:
        """Return the ancestors of this path.

        Args:
            strict: If True, the path itself will not be included in the result.

        Returns:
            All the paths that are above this path in the hierarchy, ordered from the
            root to the parent of this path.
        """

        if self.is_root():
            if strict:
                return []
            else:
                return [self]

        ancestors = self.path.split(_PATH_SEPARATOR)
        if strict:
            *ancestors, _ = ancestors

        result = [self.root()]
        ancestor = ""
        for name in ancestors:
            ancestor = f"{ancestor}{_PATH_SEPARATOR}{name}" if ancestor else name
            result.append(SequencePath(ancestor))
        return result


class PathError(RuntimeError):
    pass


class PathNotFoundError(PathError):
    pass


class PathIsRootError(PathError):
    pass

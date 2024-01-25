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

    __slots__ = ("_parts", "_str")

    def __init__(self, path: PureSequencePath | str):
        if isinstance(path, str):
            self._parts = self.convert_to_parts(path)
            self._str = path
        elif isinstance(path, PureSequencePath):
            self._parts = path.parts
            self._str = path._str
        else:
            raise TypeError(f"Invalid type for path: {type(path)}")

    @property
    def parts(self) -> tuple[str, ...]:
        return self._parts

    @property
    def parent(self) -> Optional[PureSequencePath]:
        """Return the parent of this path.

        Returns:
            The parent of this path, or None if this path is the root path.
        """

        if self.is_root():
            return None
        else:
            return PureSequencePath.from_parts(self._parts[:-1])

    def get_ancestors(self) -> Iterable[Self]:
        """Return the ancestors of this path.

        Returns:
            All the paths that are above this path in the hierarchy, ordered from the
            current path to the root, both included.
        """

        current = self
        yield current
        while parent := current.parent:
            current = parent
            yield current

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
            raise InvalidPathFormatError(f"Invalid path: {path}")

    @classmethod
    def from_parts(cls, parts: Iterable[str]) -> PureSequencePath:
        return PureSequencePath(_PATH_SEPARATOR + _PATH_SEPARATOR.join(parts))

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
                raise InvalidPathFormatError("Invalid name format")
            if self.is_root():
                return type(self)(f"{self._str}{other}")
            else:
                return type(self)(f"{self._str}{_PATH_SEPARATOR}{other}")
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self._str)

    @classmethod
    def root(cls) -> PureSequencePath:
        """Returns the root path.

        The root path is represented by the single separator character "\".
        """

        return cls(cls.separator())

    @classmethod
    def separator(cls) -> str:
        """Returns the character used to separate path names."""

        return _PATH_SEPARATOR


def bind(path: PureSequencePath, session: "ExperimentSession") -> BoundSequencePath:
    return BoundSequencePath(path, session)


class BoundSequencePath(PureSequencePath):
    __slots__ = ("_session",)

    def __init__(self, path: PureSequencePath | str, session: "ExperimentSession"):
        super().__init__(path)
        self._session = session

    @property
    def parent(self) -> Optional[Self]:
        p = super().parent
        if p is None:
            return None
        else:
            return BoundSequencePath(p, self._session)

    def get_ancestors(self) -> Iterable[Self]:
        ancestors = super().get_ancestors()
        return (BoundSequencePath(a, self._session) for a in ancestors)

    def rebind(self, new_session: "ExperimentSession"):
        self._session = new_session

    def exists(self) -> bool:
        return self._session.paths.does_path_exists(self)

    def create(self) -> list[BoundSequencePath]:
        """Create the path and all its ancestors if they don't exist.

        Return:
            A list of paths that were created if they didn't exist.

        Raises:
            PathIsSequenceError: If an ancestor exists and is a sequence.
        """

        result = self._session.paths.create_path(self)
        return [BoundSequencePath(path, self._session) for path in unwrap(result)]

    def get_children(self) -> set[BoundSequencePath]:
        """Return the direct descendants of this path.

        Returns:
            A set of the direct descendants of this path.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
            PathIsSequenceError: If the path is a sequence.
        """

        result = self._session.paths.get_children(self)
        return {BoundSequencePath(path, self._session) for path in unwrap(result)}

    def delete(self, delete_sequences: bool = False):
        """Delete the path and all its children if they exist.

        Warnings:
            If delete_sequences is True, all sequences in the path will be deleted.

        Raises:
            PathIsSequenceError: If the path or one of its children is a sequence and
            delete_sequence is False
        """

        self._session.paths.delete_path(self, delete_sequences)

    def get_creation_date(
        self, experiment_session: "ExperimentSession"
    ) -> datetime.datetime:
        """Get the creation date of the path.

        Returns:
            The date at which the path was created.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
        """

        result = experiment_session.paths.get_path_creation_date(self)
        return unwrap(result)

    @property
    def session(self) -> "ExperimentSession":
        return self._session


class InvalidPathFormatError(ValueError):
    """Raised when a path has an invalid format."""

    pass

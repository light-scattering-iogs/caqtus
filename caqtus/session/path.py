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
    r"""Represent a path in the sequence hierarchy.

    A path is a string of names separated by a single backslash.
    For example, "\\foo\\bar" is a path with two parts, "foo" and "bar".
    The root path is the single backslash "\\".

    All methods of this class are *pure* in the sense that they do not interact with
    the storage system and only manipulate the path string.
    """

    __slots__ = ("_parts", "_str")

    def __init__(self, path: PureSequencePath | str):
        if isinstance(path, str):
            self._parts = self._convert_to_parts(path)
            self._str = path
        elif isinstance(path, PureSequencePath):
            self._parts = path.parts
            self._str = path._str
        else:
            raise TypeError(f"Invalid type for path: {type(path)}")

    @property
    def parts(self) -> tuple[str, ...]:
        r"""Return the parts of the path.

        The parts are the names that make up the path.

        The root path has no parts and this attribute is an empty tuple for it.

        Example:
            >>> path = PureSequencePath(r"\foo\bar")
            >>> path.parts
            ('foo', 'bar')
        """

        return self._parts

    @property
    def parent(self) -> Optional[PureSequencePath]:
        r"""Return the parent of this path.

        Returns:
            The parent of this path, or :data:`None` if this path is the root path.

        Example:
            >>> path = PureSequencePath(r"\foo\bar")
            >>> path.parent
            PureSequencePath("\\foo")
        """

        if self.is_root():
            return None
        else:
            return PureSequencePath.from_parts(self._parts[:-1])

    def get_ancestors(self) -> Iterable[Self]:
        r"""Return the ancestors of this path.

        Returns:
            All the paths that are above this path in the hierarchy, ordered from the
            current path to the root, both included.

            For the root path, the result will only contain the root path.

        Example:
            >>> path = PureSequencePath(r"\foo\bar\baz")
            >>> list(path.get_ancestors())
            [
                PureSequencePath("\\foo\\bar\\baz"),
                PureSequencePath("\\foo\\bar"),
                PureSequencePath("\\foo"),
                PureSequencePath("\\"),
            ]
        """

        current = self
        yield current
        while parent := current.parent:
            current = parent
            yield current

    @property
    def name(self) -> Optional[str]:
        r"""Return the last part of the path.

        The root path has no name and this attribute is None for it.

        Example:
            >>> path = PureSequencePath(r"\foo\bar")
            >>> path.name
            'bar'
        """

        if self.is_root():
            return None
        else:
            return self._parts[-1]

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
        """Check if the path is the root path."""

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
        r"""Returns the root path.

        The root path is represented by the single backslash character "\\".
        """

        return cls(cls._separator())

    @classmethod
    def _separator(cls) -> str:
        """Returns the character used to separate path names."""

        return _PATH_SEPARATOR

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        """Check if a string is a valid name."""

        return bool(_PATH_NAME_REGEX.match(name))

    @classmethod
    def _convert_to_parts(cls, path: str) -> tuple[str, ...]:
        if cls.is_valid_path(path):
            if path == _PATH_SEPARATOR:
                return tuple()
            else:
                return tuple(path.split(_PATH_SEPARATOR)[1:])
        else:
            raise InvalidPathFormatError(f"Invalid path: {path}")

    @classmethod
    def from_parts(cls, parts: Iterable[str]) -> PureSequencePath:
        """Create a path from its parts."""

        return PureSequencePath(_PATH_SEPARATOR + _PATH_SEPARATOR.join(parts))

    @classmethod
    def is_valid_path(cls, path: str) -> bool:
        """Check if a string is a valid path."""

        return bool(_PATH_REGEX.match(path))


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

    def get_descendants(self) -> set[BoundSequencePath]:
        """Return the descendants of this path.

        Returns:
            A set of the descendants of this path.

        Raises:
            PathNotFoundError: If the path does not exist in the session.
            PathIsSequenceError: If the path is a sequence.
        """

        from .sequence_collection import PathIsSequenceError

        descendants = set()
        for child in self.get_children():
            descendants.add(child)
            try:
                descendants.update(child.get_descendants())
            except PathIsSequenceError:
                pass
        return descendants

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

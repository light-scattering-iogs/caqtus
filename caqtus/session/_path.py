from __future__ import annotations

import re
from typing import Self, Optional, TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    pass

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
        """

        Raises:
            InvalidPathFormatError: If the path has an invalid format.
        """
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

    def get_ancestors(self) -> Iterable[PureSequencePath]:
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
        """Add a name to the path.

        Example:
            >>> path = PureSequencePath.root()
            >>> path / "foo"
            PureSequencePath("\\foo")

        Raises:
            InvalidPathFormatError: If the name is not valid.
        """

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
        """Create a path from its parts.

        Raises:
            InvalidPathFormatError: If one of the parts is not a valid name.
        """

        return PureSequencePath(_PATH_SEPARATOR + _PATH_SEPARATOR.join(parts))

    @classmethod
    def is_valid_path(cls, path: str) -> bool:
        """Check if a string is a valid path."""

        return bool(_PATH_REGEX.match(path))

    def is_descendant_of(self, other: PureSequencePath) -> bool:
        r"""Check if this path is a descendant of another path.

        A path is a descendant of another path if it starts with the other path.

        A path is not a descendant of itself.

        Example:
            >>> path = PureSequencePath(r"\foo\bar")
            >>> other = PureSequencePath(r"\foo")
            >>> path.is_descendant_of(other)
            True
        """

        if self == other:
            return False
        else:
            return self.parts[: len(other.parts)] == other.parts


class InvalidPathFormatError(ValueError):
    """Raised when a path has an invalid format."""

    pass

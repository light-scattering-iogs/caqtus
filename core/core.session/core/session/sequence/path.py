from __future__ import annotations

import datetime
import re
import typing

import attrs

from .._return_or_raise import unwrap

if typing.TYPE_CHECKING:
    from ..experiment_session import ExperimentSession

_PATH_SEPARATOR = "."
_PATH_NAMES_REGEX = "[a-zA-Z0-9_]+"
_PATH_REGEX = re.compile(
    f"^{_PATH_NAMES_REGEX}(\\{_PATH_SEPARATOR}{_PATH_NAMES_REGEX})*$"
)


def _is_valid_path(path: str) -> bool:
    if path == "":
        return True
    return _PATH_REGEX.match(path) is not None


def convert_path_to_str(path: SequencePath | str) -> str:
    if isinstance(path, SequencePath):
        return path.path
    elif isinstance(path, str):
        return path
    else:
        raise TypeError(
            f"Expected instance of <SequencePath> or <str>, got {type(path)}"
        )


@attrs.frozen(str=False)
class SequencePath:
    """A path in the sequence hierarchy.

    A path is a string of names separated by dots. For example, "foo.bar" is a path
    with two names, "foo" and "bar".
    A given path can be a sequence or a folder. A folder can contain other folders and
    sequences. A sequence can only contain shots and cannot have children.

    Methods of this class that take an experiment session as an argument are the only
    one that actually perform io operations. The other methods are pure functions.
    """

    path: str = attrs.field(converter=convert_path_to_str)

    @path.validator  # type: ignore
    def _validate_path(self, _, value):
        if not _is_valid_path(value):
            raise ValueError(f"Invalid path: {value}")

    def __str__(self) -> str:
        return self.path

    @classmethod
    def is_valid_path(cls, path: str) -> bool:
        return _is_valid_path(path)

    def exists(self, experiment_session: "ExperimentSession") -> bool:
        return experiment_session.sequence_hierarchy.does_path_exists(self)

    def create(self, experiment_session: "ExperimentSession") -> list[SequencePath]:
        """
        Create the path and all its ancestors if they don't exist

        Args:
            experiment_session: The experiment session to use

        Return:
            list of paths that were created when they didn't exist

        Raises:
            PathIsSequenceError: If an ancestor exists and is a sequence.
        """

        result = experiment_session.sequence_hierarchy.create_path(self)
        return unwrap(result)

    def delete(
        self, experiment_session: "ExperimentSession", delete_sequences: bool = False
    ):
        """
        Delete the path and all its children if they exist

        Warnings:
            If delete_sequences is True, all sequences in the path will be deleted.

        Args:
            experiment_session: The experiment session to use
            delete_sequences: If False, raise an error if the path or one of its
            children is a sequence.

        Raises:
            RuntimeError: If the path or one of its children is a sequence and
            delete_sequence is False
        """

        experiment_session.sequence_hierarchy.delete_path(self, delete_sequences)

    def get_contained_sequences(
        self, experiment_session: "ExperimentSession"
    ) -> list[SequencePath]:
        """Return the children of this path that are sequences, including this path.

        Args:
            experiment_session: The experiment session to use.

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

    def is_root(self) -> bool:
        return self.path == ""

    def has_children(self, experiment_session: "ExperimentSession") -> int:
        return bool(self.get_child_count(experiment_session))

    def get_child_count(self, experiment_session: "ExperimentSession") -> int:
        return len(self.get_children(experiment_session))

    def get_children(
        self, experiment_session: "ExperimentSession"
    ) -> set[SequencePath]:
        """Return the direct descendants of this path.

        Args:
            experiment_session: The experiment session to look in.

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

        Args:
            experiment_session: The experiment session to look in.

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

    @classmethod
    def root(cls):
        return cls("")

    @property
    def name(self):
        return self.path.split(_PATH_SEPARATOR)[-1]

    @property
    def depth(self):
        if self.path == "":
            return -1
        else:
            return self.path.count(_PATH_SEPARATOR)

    def __truediv__(self, other) -> SequencePath:
        if isinstance(other, str):
            if not re.match(_PATH_NAMES_REGEX, other):
                raise ValueError("Invalid name format")
            if self.is_root():
                return SequencePath(other)
            else:
                return SequencePath(f"{self.path}{_PATH_SEPARATOR}{other}")

        else:
            raise TypeError(f"Can only append str to SequencePath not {type(other)}")


class PathNotFoundError(RuntimeError):
    def __init__(self, path: SequencePath):
        super().__init__(f"Path not found: {path}")


class PathIsRootError(RuntimeError):
    pass

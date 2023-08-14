import datetime
import re
import typing

if typing.TYPE_CHECKING:
    from experiment.session import ExperimentSession

_PATH_SEPARATOR = "."
_PATH_NAMES_REGEX = "[a-zA-Z0-9_]+"
_PATH_REGEX = re.compile(
    f"^{_PATH_NAMES_REGEX}(\\{_PATH_SEPARATOR}{_PATH_NAMES_REGEX})*$"
)


class SequencePath:
    def __init__(self, path: str):
        if self.is_valid_path(path):
            self._path = path
        else:
            raise ValueError(f"Invalid path format: '{path}'")

    @classmethod
    def is_valid_path(cls, path: str) -> bool:
        if path == "":
            return True
        return _PATH_REGEX.match(path) is not None

    def exists(self, experiment_session: "ExperimentSession") -> bool:
        return experiment_session.sequence_hierarchy.does_path_exists(self)

    def create(self, experiment_session: "ExperimentSession") -> list["SequencePath"]:
        """
        Create the path and all its ancestors if they don't exist

        Args:
            experiment_session: The experiment session to use

        Return:
            list of paths that were created when they didn't exist

        Raises:
            PathIsSequenceError: If an ancestor exists and is a sequence
        """

        return experiment_session.sequence_hierarchy.create_path(self)

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
    ) -> list["SequencePath"]:
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
        return experiment_session.sequence_hierarchy.is_sequence_path(self)

    def is_root(self) -> bool:
        return self._path == ""

    def has_children(self, experiment_session: "ExperimentSession") -> int:
        return bool(self.get_child_count(experiment_session))

    def get_child_count(self, experiment_session: "ExperimentSession") -> int:
        return len(self.get_children(experiment_session))

    def get_children(
        self, experiment_session: "ExperimentSession"
    ) -> set["SequencePath"]:
        """Return the direct descendants of this path."""

        return experiment_session.sequence_hierarchy.get_path_children(self)

    def get_creation_date(
        self, experiment_session: "ExperimentSession"
    ) -> datetime.datetime:
        return experiment_session.sequence_hierarchy.get_path_creation_date(self)

    def get_ancestors(self, strict: bool = True) -> list["SequencePath"]:
        """Return the ancestors of this path.

        Args:
            strict: If True, the path itself will not be included in the result.

        Returns:
            All the paths that are above this path in the hierarchy.
        """

        ancestors = self._path.split(_PATH_SEPARATOR)
        if strict:
            *ancestors, _ = ancestors

        result = []
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
        return self._path.split(_PATH_SEPARATOR)[-1]

    @property
    def depth(self):
        if self._path == "":
            return -1
        else:
            return self._path.count(_PATH_SEPARATOR)

    def __repr__(self):
        return f"SequencePath({self._path!r})"

    def __str__(self):
        return self._path

    def __eq__(self, other):
        if isinstance(other, SequencePath):
            return self._path == other._path
        elif isinstance(other, str):
            return self._path == other
        return False

    def __truediv__(self, other) -> "SequencePath":
        if isinstance(other, str):
            if not re.match(_PATH_NAMES_REGEX, other):
                raise ValueError("Invalid name format")
            if self.is_root():
                return SequencePath(other)
            else:
                return SequencePath(f"{self._path}{_PATH_SEPARATOR}{other}")

        else:
            raise TypeError(f"Can only append str to SequencePath not {type(other)}")

    def __hash__(self):
        return hash(self._path)


class PathNotFoundError(Exception):
    pass

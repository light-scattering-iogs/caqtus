import re
from typing import Self

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy_utils import Ltree

from experiment.session import ExperimentSession
from sql_model import SequencePathModel

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

    def exists(self, experiment_session: ExperimentSession):
        session = experiment_session.get_sql_session()
        return (
            session.scalar(
                select(SequencePathModel).filter(
                    SequencePathModel.path == Ltree(self._path)
                )
            )
            is not None
        )

    def create(self, experiment_session: ExperimentSession) -> list["SequencePath"]:
        """
        Create the path and all its ancestors if they don't exist

        Args:
            experiment_session: The experiment session to use

        Return:
            list of paths that were created when they didn't exist

        Raises:
            RuntimeError: If an ancestor exists and is a sequence
        """
        session = experiment_session.get_sql_session()

        created_path: list[SequencePath] = []

        for ancestor in self.get_ancestors(strict=False):
            if ancestor.exists(experiment_session):
                if ancestor.is_sequence(experiment_session):
                    raise RuntimeError(
                        f"Cannot create path {self} because a sequence already exists"
                        f" in this path {ancestor}"
                    )
            else:
                SequencePathModel.create_path(str(ancestor), session)
                created_path.append(ancestor)
        return created_path

    def delete(
        self, experiment_session: ExperimentSession, delete_sequences: bool = False
    ):
        """
        Delete the path and all its children if they exist

        Warnings:
            !!! If delete_sequences is True, all sequences in the path will be deleted

        Args:
            experiment_session: The experiment session to use
            delete_sequences: If False, raise an error if the path or one of its
            children is a sequence

        Raises:
            RuntimeError: If the path or one of its children is a sequence and
            delete_sequence is False
        """

        session = experiment_session.get_sql_session()

        if not delete_sequences:
            if sub_sequences := self.get_contained_sequences(experiment_session):
                raise RuntimeError(
                    f"Cannot delete a path that contains sequences: {sub_sequences}"
                )

        session.delete(self._query_model(session))
        session.flush()

    def get_contained_sequences(
        self, experiment_session: ExperimentSession
    ) -> list["SequencePath"]:
        """
        Check if the path or one of its children is a sequence

        Args:
            experiment_session: The experiment session to use

        Return:
            A list of all sequences inside theis path and all its descendants
        """

        if self.is_sequence(experiment_session):
            return [self]

        result = []
        for child in self.get_children(experiment_session):
            result += child.get_contained_sequences(experiment_session)
        return result

    def is_folder(self, experiment_session: ExperimentSession) -> bool:
        return not self.is_sequence(experiment_session)

    def is_sequence(self, experiment_session: ExperimentSession) -> bool:
        path = self._query_model(experiment_session.get_sql_session())
        return bool(path.sequence)

    def is_root(self) -> bool:
        return self._path == ""

    def has_children(self, experiment_session: ExperimentSession) -> int:
        return bool(self.child_count(experiment_session))

    def child_count(self, experiment_session: ExperimentSession) -> int:
        return len(self.get_children(experiment_session))

    def get_children(self, experiment_session: ExperimentSession):
        session = experiment_session.get_sql_session()
        path = self._query_model(session)
        if path.sequence:
            raise RuntimeError("Cannot check children of a sequence")
        return [SequencePath(str(child.path)) for child in path.children]

    def get_ancestors(self, strict: bool = True) -> list["SequencePath"]:
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

    def _query_model(self, session: Session) -> SequencePathModel:
        stmt = select(SequencePathModel).where(
            SequencePathModel.path == Ltree(self._path)
        )
        result = session.execute(stmt)
        # noinspection PyTypeChecker
        if path := result.scalar():
            return path
        else:
            raise PathNotFoundError(f"Could not find path '{self._path}' in database")

    @classmethod
    def query_path_models(cls, paths: list[Self], session: ExperimentSession) -> list[SequencePathModel]:
        stmt = select(SequencePathModel).where(
            SequencePathModel.path.in_([Ltree(path._path) for path in paths])
        )
        result = session.get_sql_session().execute(stmt)
        return result.scalars().all()


class PathNotFoundError(Exception):
    pass

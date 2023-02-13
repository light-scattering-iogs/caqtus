import re

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy_utils import Ltree

from .model import SequencePathModel

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
            raise ValueError(f"Invalid path format: {path}")

    @classmethod
    def is_valid_path(cls, path: str) -> bool:
        if path == "":
            return True
        return _PATH_REGEX.match(path) is not None

    def exists(self, session: Session):
        return (
            session.scalar(
                select(SequencePathModel).filter(
                    SequencePathModel.path == Ltree(self._path)
                )
            )
            is not None
        )

    def create(self, session: Session) -> list["SequencePath"]:
        """
        Create the path and all its ancestors if they don't exist

        Args:
            session: The database session to use

        Return:
            list of paths that were created when they didn't exist

        Raises:
            RuntimeError: If an ancestor exists and is a sequence
        """

        created_path: list[SequencePath] = []

        for ancestor in self.get_ancestors(strict=False):
            if ancestor.exists(session):
                if ancestor.is_sequence(session):
                    raise RuntimeError(
                        f"Cannot create path {self} because a sequence already exists"
                        f" in this path {ancestor}"
                    )
            else:
                SequencePathModel.create_path(ancestor, session)
                created_path.append(ancestor)
        return created_path

    def is_folder(self, session) -> bool:
        return not self.is_sequence(session)

    def is_sequence(self, session) -> bool:
        path = self.query_model(session)
        return bool(path.sequence)

    def is_root(self) -> bool:
        return self._path == ""

    def has_children(self, session: Session) -> int:
        return bool(self.child_count(session))

    def child_count(self, session: Session) -> int:
        return len(self.get_children(session))

    def get_children(self, session: Session):
        path = self.query_model(session)
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
            raise TypeError("Can only append str to SequencePath")

    def query_model(self, session) -> SequencePathModel:
        stmt = select(SequencePathModel).where(
            SequencePathModel.path == Ltree(self._path)
        )
        result = session.execute(stmt)
        # noinspection PyTypeChecker
        if path := result.scalar():
            return path
        else:
            raise PathNotFoundError(f"Could not find path '{self._path}' in database")


class PathNotFoundError(Exception):
    pass

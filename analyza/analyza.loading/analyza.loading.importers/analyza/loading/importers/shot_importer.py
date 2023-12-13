from abc import ABC
from typing import Protocol, TypeVar, Mapping

from core.session import ExperimentSession
from core.session.sequence import Shot
from core.types import Parameter, Image
from util import attrs

T = TypeVar("T", covariant=True)


@attrs.define
class ShotImporter(Protocol[T]):
    """Protocol for object that can import a value from a shot.

    A shot importer is a callable that takes a shot and an experiment session and returns a value of generic type T.
    """

    def __call__(self, shot: Shot, session: ExperimentSession) -> T:
        raise NotImplementedError()


class ImageImporter(ShotImporter[Image], ABC):
    """A shot importer returns an image from the shot."""

    pass


class ParametersImporter(ShotImporter[Mapping[str, Parameter]], ABC):
    pass


class AtomImporter2D(ShotImporter[dict[tuple[float, float], bool]], ABC):
    pass

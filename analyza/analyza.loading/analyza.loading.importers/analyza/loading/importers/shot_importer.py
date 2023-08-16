from typing import Protocol, TypeVar, Mapping

from attr import define

from experiment.session import ExperimentSession
from image_types import Image
from parameter_types import Parameter
from sequence.runtime import Shot

T = TypeVar("T", covariant=True)


@define
class ShotImporter(Protocol[T]):
    """Protocol for object that can import a value from a shot.

    A shot importer is a callable that takes a shot and an experiment session and returns a value of generic type T.
    """

    def __call__(self, shot: Shot, session: ExperimentSession) -> T:
        raise NotImplementedError()


class ImageImporter(ShotImporter[Image]):
    """A shot importer returns an image from the shot."""

    pass


class ParametersImporter(ShotImporter[Mapping[str, Parameter]]):
    pass


class AtomImporter2D(ShotImporter[dict[tuple[float, float], bool]]):
    pass

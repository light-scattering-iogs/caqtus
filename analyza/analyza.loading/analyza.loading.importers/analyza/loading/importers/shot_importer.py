from typing import Protocol, TypeVar

from experiment.session import ExperimentSession
from sequence.runtime import Shot

T = TypeVar("T", covariant=True)


class ShotImporter(Protocol[T]):
    def __call__(self, shot: Shot, session: ExperimentSession) -> T:
        ...

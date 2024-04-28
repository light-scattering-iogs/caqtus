from typing import TypeAlias, Protocol, TypeVar

import polars

from caqtus.session import Shot

ShotData: TypeAlias = polars.DataFrame

T = TypeVar("T")


class ShotImporter(Protocol[T]):
    """Protocol for object that can import a value from a shot.

    A shot importer is a callable that takes a shot and an experiment session and
    returns a value of generic type T.
    """

    def __call__(self, shot: Shot) -> T:
        raise NotImplementedError()


DataImporter: TypeAlias = ShotImporter[polars.DataFrame]
LazyDataImporter: TypeAlias = ShotImporter[polars.LazyFrame]

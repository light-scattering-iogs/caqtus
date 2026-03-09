from typing import TypeAlias, Protocol

import polars

from caqtus.session import Shot


class ShotImporter[T](Protocol):
    """Protocol for object that can import a value from a shot.

    A shot importer is a callable that takes a shot returns a value of generic type T.
    """

    def __call__(self, shot: Shot) -> T:
        raise NotImplementedError()


#: Type alias for a data importer that imports data from a shot.
DataImporter: TypeAlias = ShotImporter[polars.DataFrame]

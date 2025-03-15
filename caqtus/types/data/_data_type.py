from __future__ import annotations

import abc
from typing import TypeAlias

import attrs
import numpy as np
import polars

from caqtus.types.image.roi import RectangularROI

#: A type alias for numpy arrays.
type Array = np.ndarray


StructuredData: TypeAlias = (
    dict[str, "StructuredData"]
    | list["StructuredData"]
    | float
    | int
    | str
    | bool
    | None
)
"""A recursive union of basic types.

It can be used to represent complex data, possibly nested.
"""

type Data = Array | StructuredData
"""A sum type of structured data and arrays.

Only objects that are instances of this type can be saved for a shot.

Note that it is not possible to have structured data containing arrays.
"""


class DataType(abc.ABC):
    @abc.abstractmethod
    def to_polars_dtype(self) -> polars.DataType:
        raise NotImplementedError

    @abc.abstractmethod
    def to_polars_value(self, value: Data):
        raise NotImplementedError

    @abc.abstractmethod
    def is_saved_as_array(self) -> bool:
        raise NotImplementedError


@attrs.frozen
class ImageType(DataType):
    """A data type for images."""

    roi: RectangularROI

    def to_polars_dtype(self) -> polars.DataType:
        return polars.Array(polars.Float64, (self.roi.width, self.roi.height))

    def to_polars_value(self, value: Data):
        if not isinstance(value, np.ndarray):
            raise ValueError("Expected an array")
        return value.astype(np.float64)

    def is_saved_as_array(self) -> bool:
        return True

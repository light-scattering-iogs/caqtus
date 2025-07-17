from __future__ import annotations

import abc
from typing import TypeAlias

import attrs
import h5py
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

type DataType = ScalarDataType | ArrayDType

type ScalarDataType = UInt64


@attrs.define
class UInt64:
    @staticmethod
    def to_hdf5_dtype() -> np.dtype:
        return np.dtype(np.uint64)

    def unstructure(self) -> str:
        return "UInt64"

    def to_hdf5_value(self, value: Data) -> np.ndarray:
        if not isinstance(value, (int, np.integer)):
            raise ValueError(f"Expected an integer, got {value!r}.")
        return np.uint64(value)


@attrs.define
class ArrayDType:
    inner: DataType
    shape: tuple[int, ...]

    def to_hdf5_dtype(self) -> np.dtype:
        inner_dtype = self.inner.to_hdf5_dtype()
        return np.dtype([("", inner_dtype, self.shape)])

    def unstructure(self):
        return {"Array": {"inner": self.inner.unstructure(), "shape": list(self.shape)}}

    def to_hdf5_value(self, value) -> np.ndarray:
        if not isinstance(value, np.ndarray):
            raise ValueError("Expected an array")
        if value.shape != self.shape:
            raise ValueError(f"Expected shape {self.shape}, got {value.shape}")
        # return np.void(value, dtype=self.to_hdf5_dtype())
        return value.astype(self.inner.to_hdf5_dtype())


@attrs.define
class List:
    inner: DataType

    def to_hdf5_dtype(self) -> np.dtype:
        return h5py.vlen_dtype(self.inner.to_hdf5_dtype())

    def unstructure(self) -> str:
        return {"List": {"inner": self.inner.unstructure()}}

    def to_hdf5_value(self, value: Data) -> np.ndarray:
        if not isinstance(value, list):
            raise ValueError(f"Expected a list, got {value!r}.")
        return value


class _DataType(abc.ABC):
    @abc.abstractmethod
    def to_polars_dtype(self) -> polars.DataType:
        raise NotImplementedError

    @abc.abstractmethod
    def to_polars_value(self, value: Data):
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def is_saved_as_array() -> bool:
        raise NotImplementedError


@attrs.frozen
class ImageType:
    """A data type for images."""

    roi: RectangularROI

    def to_polars_dtype(self) -> polars.DataType:
        return polars.Array(polars.Float64, (self.roi.width, self.roi.height))

    def to_polars_value(self, value: Data):
        if not isinstance(value, np.ndarray):
            raise ValueError("Expected an array")
        return value.astype(np.float64)

    @staticmethod
    def is_saved_as_array() -> bool:
        return True

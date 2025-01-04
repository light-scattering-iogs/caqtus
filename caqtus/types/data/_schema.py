from __future__ import annotations

import abc
from collections.abc import Mapping, Sequence, Callable
from functools import cached_property
from typing import Any, Protocol, TypeVar, Generic, runtime_checkable

import attrs
import hypothesis.strategies as st
import msgpack
import numpy as np
import polars as pl
from hypothesis.extra.numpy import arrays

ARRAY_TYPE = 1


class DataType[S, U](Protocol):
    """Represent the type that some data can have."""

    def dumps(self, value: S) -> bytes:
        """Converts value compatible with this type to bytes.

        Raises:
            TypeError: If the value is incompatible with this data type.

        Examples:
            >>> dtype = Struct(a=Int(), b=Boolean())
            >>> dtype.dumps(45)
            b'\x92\x00\xc3'
        """

        return msgpack.dumps(self.unstructure_hook(value))  # type: ignore[reportReturnType]

    def loads(self, data: bytes) -> S:
        """Converts bytes to value compatible with this type.

        Raises:
            TypeError: If the data is incompatible with this type.

        Examples:
            >>> dtype = Struct(a=Int(), b=Boolean())
            >>> dtype.loads(b'\x92\x00\xc3')
            {'a': 0, 'b': True}
        """

        return self.structure_hook(msgpack.loads(data))  # type: ignore[reportArgumentType]

    @property
    def unstructure_hook(self) -> Callable[[S], U]: ...

    @property
    def structure_hook(self) -> Callable[[U], S]: ...

    @abc.abstractmethod
    def to_polars_dtype(self) -> pl.DataType:
        """Converts this type to a Polars data type.

        Examples:
            >>> dtype = Struct(a=Int(), b=Boolean())
            >>> dtype.to_polars_dtype()
            polars.Struct({'a': polars.Int64, 'b': polars.Boolean})
        """

        ...

    def value_strategy(self) -> st.SearchStrategy:
        """Returns a strategy to generate values compatible with this type.

        Examples:
            >>> dtype = Struct(a=Int(), b=Boolean())
            >>> dtype.value_strategy().example()
            {'a': -9203730269376721195, 'b': True}
        """

        ...


@attrs.frozen
class Float(DataType[float, float]):
    """Represents a floating point number."""

    @property
    def unstructure_hook(self) -> Callable[[Any], float]:
        return float

    @property
    def structure_hook(self) -> Callable[[Any], float]:
        return self._hook

    @staticmethod
    def _hook(value):
        if not isinstance(value, float):
            raise ValueError(f"expected float, not {value}")
        return value

    def to_polars_dtype(self) -> pl.Float64:
        return pl.Float64()

    def value_strategy(self) -> st.SearchStrategy:
        return st.floats()


@attrs.frozen
class Int(DataType[int, int]):
    """Represents an integer number."""

    @property
    def unstructure_hook(self) -> Callable[[Any], int]:
        return int

    @property
    def structure_hook(self) -> Callable[[Any], int]:
        return self._hook

    @staticmethod
    def _hook(value):
        if not isinstance(value, int):
            raise ValueError(f"expected int, not {value}")
        return value

    def to_polars_dtype(self) -> pl.Int64:
        return pl.Int64()

    def value_strategy(self) -> st.SearchStrategy:
        return st.integers(-(2**63), 2**63 - 1)


@attrs.frozen
class Boolean(DataType[bool, bool]):
    """Represents a boolean value."""

    @property
    def unstructure_hook(self) -> Callable[[Any], bool]:
        return bool

    @property
    def structure_hook(self) -> Callable[[Any], bool]:
        return self._hook

    @staticmethod
    def _hook(value):
        if not isinstance(value, bool):
            raise ValueError(f"expected bool, not {value}")
        return value

    def to_polars_dtype(self) -> pl.Boolean:
        return pl.Boolean()

    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.bool)

    def value_strategy(self) -> st.SearchStrategy:
        return st.booleans()


@attrs.frozen
class List(DataType):
    """Represent a variable length list where all elements have the same type."""

    inner: DataType

    def dumps(self, value) -> bytes:
        return msgpack.dumps(self.unstructure_hook(value))  # type: ignore[reportReturnType]

    def loads(self, data: bytes) -> list:
        return self.structure_hook(msgpack.loads(data))  # type: ignore[reportArgumentType]

    @cached_property
    def unstructure_hook(self) -> Callable[[Any], tuple]:  # type: ignore[reportIncompatibleMethodOverride]
        inner_hook = self.inner.unstructure_hook

        def hook(value):
            return tuple(inner_hook(x) for x in value)

        return hook

    @cached_property
    def structure_hook(self) -> Callable[[tuple], list]:  # type: ignore[reportIncompatibleMethodOverride]
        inner_hook = self.inner.structure_hook

        def hook(value):
            return [inner_hook(x) for x in value]

        return hook

    def to_polars_dtype(self) -> pl.DataType:
        return pl.List(self.inner.to_polars_dtype())

    def value_strategy(self) -> st.SearchStrategy:
        return st.lists(elements=self.inner.value_strategy())


T = TypeVar("T", covariant=True)


@attrs.define(init=False)
class Struct(Generic[T]):
    """Represents a data type with several fixed fields.

    Args:
        **fields: The fields of the data type.
            The keys are the names of the fields and the values are their types.
            The fields must have at least one element.
    """

    fields: dict[str, T] = attrs.field()

    def __init__(self, **fields: T):
        sorted_names = sorted(fields.keys())
        self.fields = {name: fields[name] for name in sorted_names}

    def dumps(self, value) -> bytes:
        return msgpack.dumps(self.unstructure_hook(value))  # type: ignore[reportReturnType]

    def loads(self, data: bytes) -> dict:
        return self.structure_hook(msgpack.loads(data))  # type: ignore[reportArgumentType]

    @fields.validator  # type: ignore
    def _fields_validator(self, attribute, value):
        if len(value) == 0:
            raise ValueError(f"fields must have at least one element, not {value}")

    @cached_property
    def unstructure_hook(self: Struct[DataType]) -> Callable[[Any], tuple]:
        field_hooks = {
            name: dtype.unstructure_hook for name, dtype in self.fields.items()
        }

        def hook(value):
            return tuple(hook(value[name]) for name, hook in field_hooks.items())

        return hook

    @cached_property
    def structure_hook(self: Struct[DataType]) -> Callable[[dict], dict]:
        field_hooks = {
            name: dtype.structure_hook for name, dtype in self.fields.items()
        }

        def hook(values):
            return {
                name: hook(value)
                for (name, hook), value in zip(field_hooks.items(), values, strict=True)
            }

        return hook

    def to_polars_dtype(self: Struct[ConvertibleToPolarsDType]) -> pl.Struct:
        return pl.Struct(
            fields={
                name: dtype.to_polars_dtype() for name, dtype in self.fields.items()
            }
        )

    def to_numpy_dtype(self: Struct[ArrayInnerType]) -> np.dtype:
        return np.dtype(
            [(name, dtype.to_numpy_dtype()) for name, dtype in self.fields.items()]
        )

    def value_strategy(self: Struct[DataType]) -> st.SearchStrategy:
        return st.fixed_dictionaries(
            {name: dtype.value_strategy() for name, dtype in self.fields.items()}
        )


@attrs.frozen
class ArrayDataType(DataType):
    """Represents arrays of data with a fixed shape and type.

    Attributes:
        inner: The type of the array elements.
        shape: The shape of the array.
            It must contain at least one element.
            Each element of the tuple is the size of the corresponding dimension.
            Each element must be a strictly positive integer.
    """

    inner: ArrayInnerType = attrs.field()
    shape: Sequence[int] = attrs.field()

    @shape.validator  # type: ignore
    def _shape_validator(self, attribute, value):
        if len(value) == 0:
            raise ValueError(f"shape must have at least one element, not {value}")
        if not all(isinstance(i, int) for i in value):
            raise ValueError(f"shape must be a tuple of integers, not {value}")
        if not all(i > 0 for i in value):
            raise ValueError(f"shape must be a tuple of positive integers, not {value}")

    @inner.validator  # type: ignore
    def _inner_validator(self, attribute, value):
        if not isinstance(value, ArrayInnerType):
            raise ValueError(f"inner must be an ArrayInnerType, not {value}")

    @cached_property
    def unstructure_hook(self) -> Callable[[Any], msgpack.ExtType]:  # type: ignore[reportIncompatibleMethodOverride]
        numpy_dtype = self.inner.to_numpy_dtype()
        shape = tuple(self.shape)

        def hook(value):
            if value.shape != shape:
                raise ValueError(f"expected shape {shape}, not {value.shape}")
            data = value.astype(numpy_dtype).tobytes()
            return msgpack.ExtType(ARRAY_TYPE, data)

        return hook

    @cached_property
    def structure_hook(self) -> Callable[[msgpack.ExtType], np.ndarray]:  # type: ignore[reportIncompatibleMethodOverride]
        numpy_dtype = self.inner.to_numpy_dtype()
        shape = tuple(self.shape)

        def hook(ext: msgpack.ExtType):
            if ext.code != ARRAY_TYPE:
                raise ValueError(f"expected code {ARRAY_TYPE}, not {ext.code}")
            data = np.frombuffer(ext.data, dtype=numpy_dtype)
            return data.reshape(shape)

        return hook

    def to_polars_dtype(self) -> pl.DataType:
        return pl.Array(inner=self.inner.to_polars_dtype(), shape=tuple(self.shape))

    def value_strategy(self) -> st.SearchStrategy:
        # Needs to disallow NaNs, because for a=array([(nan,)], dtype=[('f0', '<f4')]),
        # numpy.testing.assert_equal(a, a) fails, which seems to be a bug in numpy.
        return arrays(
            dtype=self.inner.to_numpy_dtype(),
            shape=tuple(self.shape),
            elements=dict(allow_nan=False),
        )


@runtime_checkable
class ArrayInnerType(Protocol):
    """Represents the type of the elements of an array."""

    def to_numpy_dtype(self) -> np.dtype: ...

    def to_polars_dtype(self) -> pl.DataType: ...


@attrs.frozen
class Float32(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.float32)

    def to_polars_dtype(self) -> pl.Float32:
        return pl.Float32()


@attrs.frozen
class Float64(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.float64)

    def to_polars_dtype(self) -> pl.Float64:
        return pl.Float64()


@attrs.frozen
class Int8(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.int8)

    def to_polars_dtype(self) -> pl.Int8:
        return pl.Int8()


@attrs.frozen
class Int16(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.int16)

    def to_polars_dtype(self) -> pl.Int16:
        return pl.Int16()


@attrs.frozen
class Int32(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.int32)

    def to_polars_dtype(self) -> pl.Int32:
        return pl.Int32()


@attrs.frozen
class Int64(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.int64)

    def to_polars_dtype(self) -> pl.Int64:
        return pl.Int64()


@attrs.frozen
class UInt8(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.uint8)

    def to_polars_dtype(self) -> pl.UInt8:
        return pl.UInt8()


@attrs.frozen
class UInt16(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.uint16)

    def to_polars_dtype(self) -> pl.UInt16:
        return pl.UInt16()


@attrs.frozen
class UInt32(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.uint32)

    def to_polars_dtype(self) -> pl.UInt32:
        return pl.UInt32()


@attrs.frozen
class UInt64(ArrayInnerType):
    def to_numpy_dtype(self) -> np.dtype:
        return np.dtype(np.uint64)

    def to_polars_dtype(self) -> pl.UInt64:
        return pl.UInt64()


class ConvertibleToPolarsDType(Protocol):
    def to_polars_dtype(self) -> pl.DataType: ...


type DataSchema = Mapping[str, DataType]
"""Contains the name and type of each data field."""

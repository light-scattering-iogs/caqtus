from collections.abc import Mapping, Sequence, Callable
from functools import cached_property
from typing import assert_never, Any

import attrs
import msgpack
import numpy as np
from typing_extensions import TypeIs

ARRAY_TYPE = 1

type ScalarDataType = Boolean | Float | Int
type NestedDataType = ArrayDataType | Struct | List
type DataType = ScalarDataType | NestedDataType


@attrs.frozen
class Float:
    def dumps(self, value) -> bytes:
        return msgpack.dumps(self.unstructure_hook(value))

    def loads(self, data: bytes) -> float:
        return self.structure_hook(msgpack.loads(data))

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


@attrs.frozen
class Int:
    def dumps(self, value) -> bytes:
        return msgpack.dumps(self.unstructure_hook(value))

    def loads(self, data: bytes) -> int:
        return self.structure_hook(msgpack.loads(data))

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


@attrs.frozen
class Boolean:
    def dumps(self, value) -> bytes:
        return msgpack.dumps(self.unstructure_hook(value))

    def loads(self, data: bytes) -> bool:
        return self.structure_hook(msgpack.loads(data))

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


type ArrayInnerType = (
    Boolean
    | Float32
    | Float64
    | Int8
    | Int16
    | Int32
    | Int64
    | UInt8
    | UInt16
    | UInt32
    | UInt64
)


@attrs.frozen
class Float32:
    pass


@attrs.frozen
class Float64:
    pass


@attrs.frozen
class Int8:
    pass


@attrs.frozen
class Int16:
    pass


@attrs.frozen
class Int32:
    pass


@attrs.frozen
class Int64:
    pass


@attrs.frozen
class UInt8:
    pass


@attrs.frozen
class UInt16:
    pass


@attrs.frozen
class UInt32:
    pass


@attrs.frozen
class UInt64:
    pass


@attrs.frozen
class ArrayDataType:
    """Fixed shape array type.

    Attributes:
        inner: The type of the array elements.
        shape: The shape of the array.
            It must contain at least one element.
            Each element of the tuple is the size of the corresponding dimension.
            Each element must be a strictly positive integer.
    """

    inner: ArrayInnerType
    shape: Sequence[int] = attrs.field()

    def dumps(self, value) -> bytes:
        return msgpack.dumps(self.unstructure_hook(value))

    def loads(self, data: bytes) -> np.ndarray:
        return self.structure_hook(msgpack.loads(data))

    @shape.validator  # type: ignore
    def _shape_validator(self, attribute, value):
        if len(value) == 0:
            raise ValueError(f"shape must have at least one element, not {value}")
        if not all(isinstance(i, int) for i in value):
            raise ValueError(f"shape must be a tuple of integers, not {value}")
        if not all(i > 0 for i in value):
            raise ValueError(f"shape must be a tuple of positive integers, not {value}")

    @cached_property
    def unstructure_hook(self) -> Callable[[Any], msgpack.ExtType]:
        numpy_dtype = to_numpy_dtype(self.inner)
        shape = tuple(self.shape)

        def hook(value):
            if value.shape != shape:
                raise ValueError(f"expected shape {shape}, not {value.shape}")
            data = value.astype(numpy_dtype).tobytes()
            return msgpack.ExtType(ARRAY_TYPE, data)

        return hook

    @cached_property
    def structure_hook(self) -> Callable[[msgpack.ExtType], np.ndarray]:
        numpy_dtype = to_numpy_dtype(self.inner)
        shape = tuple(self.shape)

        def hook(ext: msgpack.ExtType):
            if ext.code != ARRAY_TYPE:
                raise ValueError(f"expected code {ARRAY_TYPE}, not {ext.code}")
            data = np.frombuffer(ext.data, dtype=numpy_dtype)
            return data.reshape(shape)

        return hook


@attrs.frozen
class List:
    """Variable length list type."""

    inner: DataType

    def dumps(self, value) -> bytes:
        return msgpack.dumps(self.unstructure_hook(value))

    def loads(self, data: bytes) -> list:
        return self.structure_hook(msgpack.loads(data))

    @cached_property
    def unstructure_hook(self) -> Callable[[Any], tuple]:
        inner_hook = self.inner.unstructure_hook

        def hook(value):
            return tuple(inner_hook(x) for x in value)

        return hook

    @cached_property
    def structure_hook(self) -> Callable[[tuple], list]:
        inner_hook = self.inner.structure_hook

        def hook(value):
            return [inner_hook(x) for x in value]

        return hook


@attrs.frozen
class Struct:
    """Composite data type.

    Args:
        fields: The name and type of each field.
            It must contain at least one element.

    """

    fields: dict[str, DataType] = attrs.field()

    def dumps(self, value) -> bytes:
        return msgpack.dumps(self.unstructure_hook(value))

    def loads(self, data: bytes) -> dict:
        return self.structure_hook(msgpack.loads(data))

    @fields.validator  # type: ignore
    def _fields_validator(self, attribute, value):
        if len(value) == 0:
            raise ValueError(f"fields must have at least one element, not {value}")

    @cached_property
    def unstructure_hook(self) -> Callable[[Any], dict]:
        field_hooks = {
            name: dtype.unstructure_hook for name, dtype in self.fields.items()
        }

        def hook(value):
            return {name: hook(value[name]) for name, hook in field_hooks.items()}

        return hook

    @cached_property
    def structure_hook(self) -> Callable[[dict], dict]:
        field_hooks = {
            name: dtype.structure_hook for name, dtype in self.fields.items()
        }

        def hook(value):
            return {name: hook(value[name]) for name, hook in field_hooks.items()}

        return hook


type DataSchema = Mapping[str, DataType]
"""Contains the name and type of each data field."""


def is_numeric_dtype(dtype: DataType) -> TypeIs[ScalarDataType]:
    return isinstance(dtype, Boolean | Float | Int)


def is_nested_dtype(dtype: DataType) -> TypeIs[NestedDataType]:
    return isinstance(dtype, ArrayDataType | Struct | List)


def to_numpy_dtype(dtype: ArrayInnerType) -> np.dtype:
    match dtype:
        case Boolean():
            return np.dtype(np.bool)
        case Float32():
            return np.dtype(np.float32)
        case Float64():
            return np.dtype(np.float64)
        case Int8():
            return np.dtype(np.int8)
        case Int16():
            return np.dtype(np.int16)
        case Int32():
            return np.dtype(np.int32)
        case Int64():
            return np.dtype(np.int64)
        case UInt8():
            return np.dtype(np.uint8)
        case UInt16():
            return np.dtype(np.uint16)
        case UInt32():
            return np.dtype(np.uint32)
        case UInt64():
            return np.dtype(np.uint64)
        case _:
            assert_never(dtype)

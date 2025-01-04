from collections.abc import Mapping, Sequence, Callable
from typing import assert_never, Any

import attrs
import numpy as np
from typing_extensions import TypeIs

type ScalarDataType = Boolean | Float | Int
type NestedDataType = ArrayDataType | Struct | List
type DataType = ScalarDataType | NestedDataType


@attrs.frozen
class Float:
    @staticmethod
    def validator() -> Callable[[Any], bool]:
        return lambda x: isinstance(x, float)


@attrs.frozen
class Int:
    @staticmethod
    def validator() -> Callable[[Any], bool]:
        return lambda x: isinstance(x, int)


@attrs.frozen
class Boolean:
    @staticmethod
    def validator() -> Callable[[Any], bool]:
        return lambda x: isinstance(x, bool)


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

    @shape.validator  # type: ignore
    def _shape_validator(self, attribute, value):
        if len(value) == 0:
            raise ValueError(f"shape must have at least one element, not {value}")
        if not all(isinstance(i, int) for i in value):
            raise ValueError(f"shape must be a tuple of integers, not {value}")
        if not all(i > 0 for i in value):
            raise ValueError(f"shape must be a tuple of positive integers, not {value}")

    def validator(self) -> Callable[[Any], bool]:
        numpy_dtype = to_numpy_dtype(self.inner)
        shape = tuple(self.shape)

        def fun(x):
            return x.shape == shape and x.dtype == numpy_dtype

        return fun


@attrs.frozen
class List:
    """Variable length list type."""

    inner: DataType

    def validator(self) -> Callable[[Any], bool]:
        inner_validator = self.inner.validator()

        def fun(x):
            return all(inner_validator(i) for i in x)

        return fun


@attrs.frozen
class Struct:
    """Composite data type.

    Args:
        fields: The name and type of each field.
            It must contain at least one element.

    """

    fields: Mapping[str, DataType] = attrs.field()

    @fields.validator  # type: ignore
    def _fields_validator(self, attribute, value):
        if len(value) == 0:
            raise ValueError(f"fields must have at least one element, not {value}")

    def validator(self) -> Callable[[Any], bool]:
        field_validators = {
            name: dtype.validator() for name, dtype in self.fields.items()
        }

        def validate(x):
            if not isinstance(x, Mapping):
                return False
            if x.keys() != self.fields.keys():
                return False
            return all(field_validators[name](value) for name, value in x.items())

        return validate


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

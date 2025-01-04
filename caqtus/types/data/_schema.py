from collections.abc import Mapping, Sequence
from typing import assert_never

import attrs
import numpy as np
from typing_extensions import TypeIs

type NumericDataType = (
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
type NestedDataType = ArrayDataType | Struct | List
type DataType = NumericDataType | NestedDataType


@attrs.frozen
class Boolean:
    pass


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

    inner: NumericDataType
    shape: Sequence[int] = attrs.field()

    @shape.validator  # type: ignore
    def _shape_validator(self, attribute, value):
        if len(value) == 0:
            raise ValueError(f"shape must have at least one element, not {value}")
        if not all(isinstance(i, int) for i in value):
            raise ValueError(f"shape must be a tuple of integers, not {value}")
        if not all(i > 0 for i in value):
            raise ValueError(f"shape must be a tuple of positive integers, not {value}")


@attrs.frozen
class List:
    """Variable length list type."""

    inner: DataType


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


type DataSchema = Mapping[str, DataType]
"""Contains the name and type of each data field."""


def is_numeric_dtype(dtype: DataType) -> TypeIs[NumericDataType]:
    return isinstance(
        dtype,
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
        | UInt64,
    )


def is_nested_dtype(dtype: DataType) -> TypeIs[NestedDataType]:
    return isinstance(dtype, ArrayDataType | Struct | List)


def to_numpy_dtype(dtype: NumericDataType) -> np.dtype:
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

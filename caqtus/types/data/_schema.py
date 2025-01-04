from collections.abc import Mapping

import attrs

type NumericDataType = Float32 | Float64 | Int8 | Int16 | Int32 | Int64 | UInt8 | UInt16 | UInt32 | UInt64
type NestedDataType = Array | Struct | List
type DataType = NumericDataType | NestedDataType


class Float32:
    pass


class Float64:
    pass


class Int8:
    pass


class Int16:
    pass


class Int32:
    pass


class Int64:
    pass


class UInt8:
    pass


class UInt16:
    pass


class UInt32:
    pass


class UInt64:
    pass


@attrs.frozen
class Array:
    """Fixed shape array type.

    Attributes:
        inner: The type of the array elements.
        shape: The shape of the array.
            Each element of the tuple is the size of the corresponding dimension.
            Each element must be a strictly positive integer.
    """

    inner: NumericDataType
    shape: tuple[int, ...] = attrs.field()

    @shape.validator  # type: ignore
    def _shape_validator(self, attribute, value):
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
    """Composite data type."""

    fields: Mapping[str, DataType]


type DataSchema = Mapping[str, DataType]
"""Contains the name and type of each data field."""

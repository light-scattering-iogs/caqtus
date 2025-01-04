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
    inner: NumericDataType
    shape: tuple[int, ...]


@attrs.frozen
class List:
    """Variable length list type."""

    inner: DataType


@attrs.frozen
class Struct:
    """Composite data type."""

    fields: Mapping[str, DataType]

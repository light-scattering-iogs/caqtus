from typing import assert_never, Optional, Any

from hypothesis.extra.numpy import arrays
from hypothesis.strategies import (
    SearchStrategy,
    booleans,
    floats,
    integers,
    lists,
    tuples,
    composite,
)

from caqtus.types.data import (
    DataType,
    NumericDataType,
    NestedDataType,
    Boolean,
    Float32,
    Float64,
    Int8,
    Int16,
    Int32,
    Int64,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
    is_numeric_dtype,
    ArrayDataType,
    List,
    Struct,
)
from caqtus.types.data._schema import to_numpy_dtype, is_nested_dtype
from .data_type import data_types


def data_values(dtype: Optional[DataType] = None) -> SearchStrategy:
    if dtype is None:
        return data_types().flatmap(data_values)
    else:
        return _data_values(dtype)


@composite
def dtypes_and_values(draw) -> tuple[DataType, Any]:
    dtype = draw(data_types())
    value = draw(data_values(dtype))
    return dtype, value


def _data_values(dtype: DataType) -> SearchStrategy:
    if is_numeric_dtype(dtype):
        return numeric_data_values(dtype)
    else:
        assert is_nested_dtype(dtype)
        return nested_data_values(dtype)


def numeric_data_values(dtype: NumericDataType) -> SearchStrategy:
    match dtype:
        case Boolean():
            return booleans()
        case Float32():
            return floats(width=32)
        case Float64():
            return floats(width=64)
        case Int8():
            return integers(min_value=-(2**7), max_value=2**7 - 1)
        case Int16():
            return integers(min_value=-(2**15), max_value=2**15 - 1)
        case Int32():
            return integers(min_value=-(2**31), max_value=2**31 - 1)
        case Int64():
            return integers(min_value=-(2**63), max_value=2**63 - 1)
        case UInt8():
            return integers(min_value=0, max_value=2**8 - 1)
        case UInt16():
            return integers(min_value=0, max_value=2**16 - 1)
        case UInt32():
            return integers(min_value=0, max_value=2**32 - 1)
        case UInt64():
            return integers(min_value=0, max_value=2**64 - 1)
        case _:
            assert_never(dtype)


def nested_data_values(dtype: NestedDataType) -> SearchStrategy:
    match dtype:
        case ArrayDataType(inner=inner, shape=shape):
            return arrays(dtype=to_numpy_dtype(inner), shape=tuple(shape))
        case List(inner=inner):
            return lists(data_values(inner))
        case Struct() as struct:
            return struct_values(struct)
        case _:
            assert_never(dtype)


def struct_values(dtype: Struct) -> SearchStrategy:
    def to_dict(values):
        return {key: value for key, value in zip(dtype.fields.keys(), values)}

    return tuples(*(data_values(dtype) for dtype in dtype.fields.values())).map(to_dict)

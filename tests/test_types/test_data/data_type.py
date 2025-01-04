from hypothesis.strategies import (
    SearchStrategy,
    one_of,
    sampled_from,
    lists as _lists,
    integers,
    builds,
    recursive,
    dictionaries,
    text,
)

from caqtus.types.data import (
    DataType,
    ScalarDataType,
    NestedDataType,
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
    ArrayDataType,
    ArrayInnerType,
    List,
    Struct,
    Boolean,
    Float,
    Int,
)


def data_types() -> SearchStrategy[DataType]:
    return recursive(
        one_of(scalar_data_types(), arrays()), nested_data_types, max_leaves=3
    )


def scalar_data_types() -> SearchStrategy[ScalarDataType]:
    return sampled_from(
        [
            Boolean(),
            Int(),
            Float(),
        ]
    )


def nested_data_types(
    dtype: SearchStrategy[DataType],
) -> SearchStrategy[NestedDataType]:
    return one_of(dtype.map(List), structs(dtype))


def structs(dtype: SearchStrategy[DataType]) -> SearchStrategy[Struct]:
    return dictionaries(keys=text(), values=dtype, min_size=1, max_size=10).map(
        lambda d: Struct(**d)
    )


def arrays() -> SearchStrategy[ArrayDataType]:
    return builds(ArrayDataType, inner=array_dtypes(), shape=_array_shape)


def array_dtypes() -> SearchStrategy[ArrayInnerType]:
    return sampled_from(
        [
            Boolean(),
            Float32(),
            Float64(),
            Int8(),
            Int16(),
            Int32(),
            Int64(),
            UInt8(),
            UInt16(),
            UInt32(),
            UInt64(),
        ]
    )


def lists() -> SearchStrategy[List]:
    return data_types().map(List)


_array_shape = _lists(integers(min_value=1, max_value=100), min_size=1, max_size=3)

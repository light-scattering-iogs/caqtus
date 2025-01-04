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
    NumericDataType,
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
    List,
    Struct,
    Boolean,
)


def data_types() -> SearchStrategy[DataType]:
    return recursive(
        one_of(numeric_data_types(), arrays()), nested_data_types, max_leaves=3
    )


def numeric_data_types() -> SearchStrategy[NumericDataType]:
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


def nested_data_types(
    dtype: SearchStrategy[DataType],
) -> SearchStrategy[NestedDataType]:
    return one_of(dtype.map(List), structs(dtype))


def structs(dtype: SearchStrategy[DataType]) -> SearchStrategy[Struct]:
    return dictionaries(keys=text(), values=dtype, min_size=1).map(Struct)


def arrays() -> SearchStrategy[ArrayDataType]:
    return builds(ArrayDataType, inner=numeric_data_types(), shape=_array_shape)


def lists() -> SearchStrategy[List]:
    return data_types().map(List)


_array_shape = _lists(integers(min_value=1, max_value=1000), min_size=1, max_size=3)

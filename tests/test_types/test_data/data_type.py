from hypothesis.strategies import SearchStrategy, one_of, sampled_from

from caqtus.types.data import (
    DataType,
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
)


def data_types() -> SearchStrategy[DataType]:
    return one_of(numeric_data_types())


def numeric_data_types() -> SearchStrategy[DataType]:
    return sampled_from(
        [
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

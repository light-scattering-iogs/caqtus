"""This module define the type of data that can be saved for a shot."""

from ._data_label import DataLabel, is_data_label
from ._data_type import Data, Array, StructuredData
from ._is_data import is_data
from ._schema import (
    DataType,
    Boolean,
    Int,
    Float,
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
)

__all__ = [
    "Data",
    "Array",
    "StructuredData",
    "is_data",
    "DataLabel",
    "is_data_label",
    "DataType",
    "Boolean",
    "Int",
    "Float",
    "Float32",
    "Float64",
    "Int8",
    "Int16",
    "Int32",
    "Int64",
    "UInt8",
    "UInt16",
    "UInt32",
    "UInt64",
    "ArrayDataType",
    "ArrayInnerType",
    "List",
    "Struct",
]

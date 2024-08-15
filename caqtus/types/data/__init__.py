"""This module define the type of data that can be saved for a shot."""

from .data_label import DataLabel, is_data_label
from ._data_type import Data, Array, StructuredData
from .is_data import is_data

__all__ = ["Data", "Array", "StructuredData", "is_data", "DataLabel", "is_data_label"]

"""This module contains utilities to generate complex values for the output of a device.

It is convenient to transform input values given by the user into output values that
a device should generate.
This module contains classes that can be used to construct complex tree structures that
represent user defined transformations.
"""

from ._converter import get_converter
from ._output_mapping import LinearInterpolation
from .transformation import Transformation, evaluate

__all__ = [
    "Transformation",
    "LinearInterpolation",
    "get_converter",
    "evaluate",
]

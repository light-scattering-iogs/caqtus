"""Contains utilities to generate complex values for the output of a device.

It is convenient to transform input values given by the user into output values that
a device should generate.
This module contains classes that can be used to construct complex tree structures that
represent user defined transformations.
"""

from ._converter import converter, structure_evaluable_output
from ._output_mapping import LinearInterpolation
from ._transformation import (
    Transformation,
    evaluate,
    EvaluableOutput,
    evaluable_output_validator,
)


__all__ = [
    "Transformation",
    "LinearInterpolation",
    "evaluate",
    "EvaluableOutput",
    "converter",
    "evaluable_output_validator",
    "structure_evaluable_output",
]

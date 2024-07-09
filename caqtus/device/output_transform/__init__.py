"""This module contains utilities to generate complex values for the output of a device.

It is convenient to transform input values given by the user into output values that
a device should generate.
This module contains classes that can be used to construct complex tree structures that
represent user defined transformations.
"""

import functools

import cattrs.strategies

from ._converter import converter, structure_evaluable_output
from ._output_mapping import LinearInterpolation
from .transformation import Transformation, evaluate, EvaluableOutput

cattrs.strategies.include_subclasses(
    Transformation,
    converter=converter,
    union_strategy=functools.partial(
        cattrs.strategies.configure_tagged_union, tag_name="type"
    ),
)
converter.register_structure_hook(EvaluableOutput, structure_evaluable_output)

__all__ = [
    "Transformation",
    "LinearInterpolation",
    "evaluate",
    "EvaluableOutput",
    "converter",
]

import functools

import cattrs.strategies

from caqtus.device.output_transform import (
    EvaluableOutput,
    Transformation,
)
from caqtus.types.expression import Expression
from caqtus.utils.serialization import copy_converter

_converter = copy_converter()


@_converter.register_structure_hook
def structure_evaluable_output(data, _) -> EvaluableOutput:
    if isinstance(data, str):
        return Expression(data)
    else:
        return _converter.structure(data, Transformation)


# We need to register subclasses once they have been imported and defined.
cattrs.strategies.include_subclasses(
    Transformation,
    converter=_converter,
    union_strategy=functools.partial(
        cattrs.strategies.configure_tagged_union, tag_name="type"
    ),
)


def get_converter():
    return _converter

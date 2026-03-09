import functools
from collections.abc import Callable
from typing import Any

import cattrs.strategies

from caqtus.device.output_transform import (
    EvaluableOutput,
    Transformation,
    LinearInterpolation,
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
    subclasses=(LinearInterpolation,),
    union_strategy=functools.partial(
        cattrs.strategies.configure_tagged_union, tag_name="type"
    ),
)


def get_converter():
    return _converter


def get_structure_hook(type_: Any) -> Callable[[Any], Any]:
    hook = _converter.get_structure_hook(type_)

    def structure_hook(data):
        return hook(data, type_)

    return structure_hook


def get_unstructure_hook(type_: Any) -> Callable[[Any], Any]:
    hook = _converter.get_unstructure_hook(type_)
    return hook

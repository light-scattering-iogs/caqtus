from typing import assert_never

import attrs
from core.types.expression import Expression
from util import serialization

from .timelane import TimeLane


@attrs.define(init=False, eq=False, repr=False)
class DigitalTimeLane(TimeLane[bool | Expression]):
    """A time lane that represents digital values over time.

    The values of a digital time lane can be a boolean: True or False, or a
    placeholder expression.
    The placeholder expression is used to represent a value that is not known
    at the time of creation of the time lane and will be evaluated at a later
    time.

    Examples:

    .. code-block:: python

       from core.session.shot import DigitalTimeLane
       from core.types.expression import Expression

       # Creates a digital time lane with known values
       lane = DigitalTimeLane([True] * 3 + [False, True])

       # Creates a digital time lane with a placeholder expression
       lane = DigitalTimeLane([Expression("x"), False, True])
    """

    pass


def union_unstructure(union: bool | Expression):
    if isinstance(union, bool):
        return union
    elif isinstance(union, Expression):
        return union.body
    else:
        assert_never(union)


def union_structure(data, _) -> bool | Expression:
    if isinstance(data, bool):
        return data
    elif isinstance(data, str):
        return Expression(data)
    else:
        raise ValueError(f"Invalid union value: {data}")


serialization.register_structure_hook(bool | Expression, union_structure)
serialization.register_unstructure_hook(bool | Expression, union_unstructure)


def unstructure_hook(lane: DigitalTimeLane):
    return {
        "spanned_values": serialization.unstructure(
            lane._spanned_values, list[tuple[bool | Expression, int]]
        )
    }


def structure_hook(data, _) -> DigitalTimeLane:
    structured = serialization.structure(
        data["spanned_values"], list[tuple[bool | Expression, int]]
    )
    return DigitalTimeLane.from_spanned_values(structured)


serialization.register_structure_hook(DigitalTimeLane, structure_hook)
serialization.register_unstructure_hook(DigitalTimeLane, unstructure_hook)

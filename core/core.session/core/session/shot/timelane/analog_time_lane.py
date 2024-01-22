from typing import assert_never

import attrs

from core.types.expression import Expression
from util import serialization
from .timelane import TimeLane


class Ramp:
    def __eq__(self, other):
        return isinstance(other, Ramp)

    def __repr__(self):
        return "Ramp()"


def unstructure_union(union: Expression | Ramp):
    if isinstance(union, Expression):
        return {"expression": union.body}
    elif isinstance(union, Ramp):
        return "ramp"
    else:
        assert_never(union)


def structure_union(data, _) -> Expression | Ramp:
    if isinstance(data, dict):
        return Expression(data["expression"])
    elif data == "ramp":
        return Ramp()
    else:
        raise ValueError(f"Invalid union value: {data}")


serialization.register_structure_hook(Expression | Ramp, structure_union)
serialization.register_unstructure_hook(Expression | Ramp, unstructure_union)


@attrs.define(init=False, eq=False, repr=False)
class AnalogTimeLane(TimeLane[Expression | Ramp]):
    pass


def unstructure_hook(lane: AnalogTimeLane):
    return {
        "spanned_values": serialization.unstructure(
            lane._spanned_values, list[tuple[Expression | Ramp, int]]
        )
    }


def structure_hook(data, _) -> AnalogTimeLane:
    structured = serialization.structure(
        data["spanned_values"], list[tuple[Expression | Ramp, int]]
    )
    return AnalogTimeLane.from_spanned_values(structured)


serialization.register_structure_hook(AnalogTimeLane, structure_hook)
serialization.register_unstructure_hook(AnalogTimeLane, unstructure_hook)

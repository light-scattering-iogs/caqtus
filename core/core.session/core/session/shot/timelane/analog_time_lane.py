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
    """A time lane that represents analog values changing over time.

    The values of an analog time lane can be a placeholder expression or a ramp.
    The placeholder expression represents a values that is constant for the given steps.
    The ramp represents a linear change from the previous step to the next step.

    The conditions below are not checked by the class, but code that evaluates the lane
    should enforce them:

    #. A ramp should not be the first or last value of the lane.
    #. There should not be two consecutive ramps in the lane. Use a single ramp block spanning multiple steps instead.
    #. Expressions representing values with units should all have the same dimension for a given lane.

    Examples:

    .. code-block:: python

        from core.session.shot import AnalogTimeLane
        from core.types.expression import Expression

        # Creates an analog time lane with known values
        lane = AnalogTimeLane([Expression("0 MHz")] + [Ramp()] * 2 + [Expression("10 MHz")])

        # Creates an analog time lane with a placeholder expression
        lane = AnalogTimeLane([Expression("2 * x"), Expression("y")])
    """

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

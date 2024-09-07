from __future__ import annotations

from numbers import Integral, Real
from typing import Mapping, Any, Optional

import attrs

import caqtus.formatter as fmt
from caqtus.device.sequencer.channel_commands.channel_output import (
    ChannelOutput,
    DimensionedSeries,
)
from caqtus.device.sequencer.instructions import Pattern
from caqtus.shot_compilation import ShotContext
from caqtus.types.expression import Expression
from caqtus.types.recoverable_exceptions import InvalidTypeError
from caqtus.types.units import Quantity, Unit, dimensionless
from caqtus.types.variable_name import DottedVariableName
from ...timing import TimeStep, number_time_steps


@attrs.define
class Constant(ChannelOutput):
    """Indicates that the output should be held at a constant value during the shot.

    The constant value is obtained by evaluating the value stored in the constant
    output within the shot context.
    Note that `constant` refers to a value constant in shot time, not necessarily
    constant across shots.
    """

    value: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return str(self.value)

    def evaluate(
        self,
        required_time_step: TimeStep,
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> DimensionedSeries:
        length = (
            prepend
            + number_time_steps(shot_context.get_shot_duration(), required_time_step)
            + append
        )
        value = self.value.evaluate(shot_context.get_variables())
        magnitude, units = split_magnitude_units(value)
        return DimensionedSeries(Pattern([magnitude]) * length, units)

    def evaluate_max_advance_and_delay(
        self,
        time_step: TimeStep,
        variables: Mapping[DottedVariableName, Any],
    ) -> tuple[int, int]:
        return 0, 0


def split_magnitude_units(value: Any) -> tuple[bool | int | float, Optional[Unit]]:
    if isinstance(value, Quantity):
        in_base_units = value.to_base_units()
        magnitude = float(in_base_units.magnitude)
        units = in_base_units.units if in_base_units.units != dimensionless else None
    elif isinstance(value, bool):
        magnitude = value
        units = None
    elif isinstance(value, Integral):
        magnitude = int(value)
        units = None
    elif isinstance(value, Real):
        magnitude = float(value)
        units = None
    else:
        raise InvalidTypeError(
            f"Constant value must be a number or a boolean, got {fmt.type_(value)}"
        )
    assert isinstance(units, Unit) or units is None
    return magnitude, units

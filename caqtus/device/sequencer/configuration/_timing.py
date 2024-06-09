from __future__ import annotations

from collections.abc import Mapping
from typing import Optional, Any

import attrs
import cattrs
import numpy as np

from caqtus.shot_compilation import ShotContext
from caqtus.types.expression import Expression
from caqtus.types.parameter import magnitude_in_unit
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from ._structure_hook import structure_channel_output
from .channel_output import ChannelOutput
from ..instructions import SequencerInstruction


@attrs.define
class Advance(ChannelOutput):
    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    advance: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.input_} << {self.advance}"

    def evaluate(
        self,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> SequencerInstruction:
        evaluated_advance = _evaluate_expression_in_unit(
            self.advance, Unit("ns"), shot_context.get_variables()
        )
        number_ticks_to_advance = round(evaluated_advance / required_time_step)
        if number_ticks_to_advance < 0:
            raise ValueError(
                f"Cannot advance by a negative number of time steps "
                f"({number_ticks_to_advance})"
            )
        if number_ticks_to_advance > prepend:
            raise ValueError(
                f"Cannot advance by {number_ticks_to_advance} time steps when only "
                f"{prepend} are available"
            )
        return self.input_.evaluate(
            required_time_step,
            required_unit,
            prepend - number_ticks_to_advance,
            append + number_ticks_to_advance,
            shot_context,
        )


# Workaround for https://github.com/python-attrs/cattrs/issues/430
advance_structure_hook = cattrs.gen.make_dict_structure_fn(
    Advance,
    serialization.converters["json"],
    input_=cattrs.override(struct_hook=structure_channel_output),
)

serialization.register_structure_hook(Advance, advance_structure_hook)


@attrs.define
class Delay(ChannelOutput):
    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    delay: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return f"{self.delay} >> {self.input_}"

    def evaluate(
        self,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> SequencerInstruction:
        evaluated_delay = _evaluate_expression_in_unit(
            self.delay, Unit("ns"), shot_context.get_variables()
        )
        number_ticks_to_delay = round(evaluated_delay / required_time_step)
        if number_ticks_to_delay < 0:
            raise ValueError(
                f"Cannot delay by a negative number of time steps "
                f"({number_ticks_to_delay})"
            )
        return self.input_.evaluate(
            required_time_step,
            required_unit,
            prepend + number_ticks_to_delay,
            append - number_ticks_to_delay,
            shot_context,
        )


# Workaround for https://github.com/python-attrs/cattrs/issues/430
delay_structure_hook = cattrs.gen.make_dict_structure_fn(
    Delay,
    serialization.converters["json"],
    input_=cattrs.override(struct_hook=structure_channel_output),
)

serialization.register_structure_hook(Delay, delay_structure_hook)


@attrs.define
class BroadenLeft(ChannelOutput):
    """Indicates that output should go high before the input pulses go high.

    The output y(t) of this operation should be high when any of the input x(s) is high
    for s in [t, t + width].

    The operation is only valid for boolean inputs, and it will produce a boolean
    output.

    It is meant to be used to compensate for finite rise times in the hardware.
    For example, if a shutter takes 10 ms to open, and we want to open it at time t, we
    can use this operation to start opening the shutter at time t - 10 ms.
    """

    input_: ChannelOutput = attrs.field(
        validator=attrs.validators.instance_of(ChannelOutput),
        on_setattr=attrs.setters.validate,
    )
    width: Expression = attrs.field(
        validator=attrs.validators.instance_of(Expression),
        on_setattr=attrs.setters.validate,
    )

    def evaluate(
        self,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> SequencerInstruction:
        raise NotImplementedError("BroadenLeft.evaluate is not implemented")


broaden_left_structure_hook = cattrs.gen.make_dict_structure_fn(
    BroadenLeft,
    serialization.converters["json"],
    input_=cattrs.override(struct_hook=structure_channel_output),
)

serialization.register_structure_hook(BroadenLeft, broaden_left_structure_hook)


def _evaluate_expression_in_unit(
    expression: Expression,
    required_unit: Optional[Unit],
    variables: Mapping[DottedVariableName, Any],
) -> np.floating:
    value = expression.evaluate(variables)
    magnitude = magnitude_in_unit(value, required_unit)
    return magnitude

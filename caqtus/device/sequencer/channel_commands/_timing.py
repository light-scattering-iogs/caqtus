from __future__ import annotations

from collections.abc import Mapping
from typing import Optional, Any

import attrs
import cattrs
import numpy as np

from caqtus.device.sequencer.channel_commands.channel_output import ChannelOutput
from caqtus.device.sequencer.instructions import SequencerInstruction
from caqtus.shot_compilation import ShotContext
from caqtus.types.expression import Expression
from caqtus.types.parameter import magnitude_in_unit
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName
from caqtus.utils import serialization
from ._calibrated_analog_mapping import TimeIndependentMapping
from ._channel_sources import is_value_source
from ._structure_hook import structure_channel_output


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


def _evaluate_max_advance_and_delay(
    channel_function: ChannelOutput,
    time_step: int,
    variables: Mapping[DottedVariableName, Any],
) -> tuple[int, int]:
    if is_value_source(channel_function):
        return 0, 0
    elif isinstance(channel_function, TimeIndependentMapping):
        advances_and_delays = [
            _evaluate_max_advance_and_delay(input_, time_step, variables)
            for input_ in channel_function.inputs()
        ]
        advances, delays = zip(*advances_and_delays)
        return max(advances), max(delays)
    elif isinstance(channel_function, Advance):
        advance = _evaluate_expression_in_unit(
            channel_function.advance, Unit("ns"), variables
        )
        if advance < 0:
            raise ValueError(f"Advance must be a positive number.")
        advance_ticks = round(advance / time_step)
        input_advance, input_delay = _evaluate_max_advance_and_delay(
            channel_function.input_, time_step, variables
        )
        return advance_ticks + input_advance, input_delay
    elif isinstance(channel_function, Delay):
        delay = _evaluate_expression_in_unit(
            channel_function.delay, Unit("ns"), variables
        )
        if delay < 0:
            raise ValueError(f"Delay must be a positive number.")
        delay_ticks = round(delay / time_step)
        input_advance, input_delay = _evaluate_max_advance_and_delay(
            channel_function.input_, time_step, variables
        )
        return input_advance, delay_ticks + input_delay
    else:
        raise NotImplementedError(
            f"Cannot evaluate max advance and delay for {channel_function}"
        )

from __future__ import annotations

from typing import Optional

import attrs

from caqtus.shot_compilation import ShotContext
from caqtus.shot_compilation.lane_compilers.timing import number_ticks, ns
from caqtus.types.expression import Expression
from caqtus.types.parameter import magnitude_in_unit
from caqtus.types.units import Unit
from caqtus.device.sequencer.channel_commands.channel_output import ChannelOutput
from caqtus.device.sequencer.instructions import SequencerInstruction, Pattern


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
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> SequencerInstruction:
        length = (
            number_ticks(0, shot_context.get_shot_duration(), required_time_step * ns)
            + prepend
            + append
        )
        value = self.value.evaluate(shot_context.get_variables())
        magnitude = magnitude_in_unit(value, required_unit)
        return Pattern([magnitude]) * length

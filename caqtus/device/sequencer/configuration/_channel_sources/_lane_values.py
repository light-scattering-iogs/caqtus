from __future__ import annotations

from typing import Optional

import attrs
from cattrs.gen import make_dict_structure_fn, override

from caqtus.device.sequencer.configuration.channel_output import ChannelOutput
from caqtus.shot_compilation import ShotContext
from caqtus.types.expression import Expression
from caqtus.types.timelane import DigitalTimeLane, AnalogTimeLane
from caqtus.types.units import Unit
from caqtus.utils import serialization, add_exc_note
from ._constant import Constant
from ...compilation._compile_digital_lane import compile_digital_lane
from ...compilation.compile_analog_lane import compile_analog_lane
from ...instructions import SequencerInstruction, Pattern


@attrs.define
class LaneValues(ChannelOutput):
    """Indicates that the output should be the values taken by a given lane.


    Attributes:
        lane: The name of the lane from which to take the values.
        default: The default value to take if the lane is absent from the shot
            time lanes.
    """

    lane: str = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )
    default: Optional[ChannelOutput] = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.instance_of(ChannelOutput)
        ),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self) -> str:
        if self.default is not None:
            return f"{self.lane} | {self.default}"
        return self.lane

    def evaluate(
        self,
        required_time_step: int,
        required_unit: Optional[Unit],
        prepend: int,
        append: int,
        shot_context: ShotContext,
    ) -> SequencerInstruction:
        """Evaluate the output of a channel as the values of a lane.

        This function will look in the shot time lanes to find the lane referenced by
        the output and evaluate the values of this lane.
        If the lane cannot be found, and the output has a default value, this default
        value will be used.
        If the lane cannot be found and there is no default value, a ValueError will be
        raised.
        """

        lane_name = self.lane
        try:
            lane = shot_context.get_lane(lane_name)
        except KeyError:
            if self.default is not None:
                return self.default.evaluate(
                    required_time_step,
                    required_unit,
                    prepend,
                    append,
                    shot_context,
                )
            else:
                raise ValueError(
                    f"Could not find lane <{lane_name}> when evaluating output "
                    f"<{self}>"
                )
        if isinstance(lane, DigitalTimeLane):
            if required_unit is not None:
                raise ValueError(
                    f"Cannot evaluate digital lane <{lane_name}> with unit "
                    f"{required_unit:~}"
                )
            with add_exc_note(f"When evaluating digital lane <{lane_name}>"):
                lane_values = compile_digital_lane(
                    lane, required_time_step, shot_context
                )
        elif isinstance(lane, AnalogTimeLane):
            with add_exc_note(f"When evaluating analog lane <{lane_name}>"):
                lane_values = compile_analog_lane(
                    lane, required_unit, required_time_step, shot_context
                )
        else:
            raise TypeError(f"Cannot evaluate values of lane with type {type(lane)}")
        prepend_pattern = prepend * Pattern([lane_values[0]])
        append_pattern = append * Pattern([lane_values[-1]])
        return prepend_pattern + lane_values + append_pattern


def structure_lane_default(default_data, _):
    # We need this custom structure hook, because in the past the default value of a
    # LaneValues was a Constant and not any ChannelOutput.
    # In that case, the type of the default value was not serialized, so we need to
    # deal with this special case.
    if default_data is None:
        return None
    elif isinstance(default_data, str):
        default_expression = serialization.structure(default_data, Expression)
        return Constant(value=default_expression)
    elif "type" in default_data:
        return serialization.structure(default_data, ChannelOutput)
    else:
        return serialization.structure(default_data, Constant)


structure_lane_values = make_dict_structure_fn(
    LaneValues,
    serialization.converters["json"],
    default=override(struct_hook=structure_lane_default),
)


def unstructure_lane_values(lane_values):
    return {
        "lane": lane_values.lane,
        "default": serialization.unstructure(
            lane_values.default, Optional[ChannelOutput]
        ),
    }


serialization.register_structure_hook(LaneValues, structure_lane_values)
serialization.register_unstructure_hook(LaneValues, unstructure_lane_values)

from __future__ import annotations

from typing import Optional

import attrs

from caqtus.device.sequencer.configuration.channel_output import ChannelOutput
from caqtus.types.expression import Expression
from caqtus.utils import serialization
from ._constant import Constant


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


def structure_lane_values(data, _):
    lane = data["lane"]
    default_data = data["default"]
    if isinstance(default_data, str):
        default_expression = serialization.structure(default_data, Expression)
        default = Constant(value=default_expression)
    else:
        default = serialization.structure(default_data, Optional[ChannelOutput])

    return LaneValues(lane=lane, default=default)


def unstructure_lane_values(lane_values):
    return {
        "lane": lane_values.lane,
        "default": serialization.unstructure(
            lane_values.default, Optional[ChannelOutput]
        ),
    }


serialization.register_structure_hook(LaneValues, structure_lane_values)
serialization.register_unstructure_hook(LaneValues, unstructure_lane_values)

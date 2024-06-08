from __future__ import annotations

from typing import Optional

import attrs
from cattrs.gen import make_dict_structure_fn, override

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

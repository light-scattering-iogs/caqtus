import decimal
from typing import Optional

import cattrs.strategies
from cattrs.gen import make_dict_structure_fn, override

from caqtus.types.expression import Expression
from caqtus.utils import serialization
from ._time_step import TimeStep
from .channel_commands import (
    CalibratedAnalogMapping,
    ChannelOutput,
    LaneValues,
    Constant,
    DeviceTrigger,
)
from .channel_commands.timing import Advance, Delay, BroadenLeft
from .trigger import TriggerEdge, Trigger

converter = serialization.copy_converter()
"""A converter than can serialize and deserialize sequencer configuration."""


def _structure_time_step(value, _) -> TimeStep:
    return decimal.Decimal(value)


converter.register_structure_hook(TimeStep, _structure_time_step)


def _unstructure_time_step(value) -> str:
    return str(value)


converter.register_unstructure_hook(TimeStep, _unstructure_time_step)


converter.register_unstructure_hook(TriggerEdge, lambda edge: edge.value)
cattrs.strategies.configure_tagged_union(Trigger, converter, tag_name="trigger type")


def structure_channel_output(data, _):
    # This is a legacy workaround for structuring ChannelOutput subclasses.
    # This is because at the beginning of the project, the type field was not serialized
    # but instead the type was inferred from the structure of the data.
    # For new data, we can use the type field to determine the type of the
    # ChannelOutput subclass, but for old data, we need to infer the type from the
    # fields present in the data.
    if "type" in data:
        return converter.structure(data, ChannelOutput)
    elif "lane" in data:
        return converter.structure(data, LaneValues)
    elif data.keys() == {"value"}:
        return converter.structure(data, Constant)
    else:
        raise ValueError(f"Cannot structure {data} as a ChannelOutput")


# Workaround for https://github.com/python-attrs/cattrs/issues/430
structure_hook = cattrs.gen.make_dict_structure_fn(
    CalibratedAnalogMapping,
    converter,
    input_=cattrs.override(struct_hook=structure_channel_output),
)

converter.register_structure_hook(CalibratedAnalogMapping, structure_hook)

# Workaround for https://github.com/python-attrs/cattrs/issues/430
advance_structure_hook = cattrs.gen.make_dict_structure_fn(
    Advance,
    converter,
    input_=cattrs.override(struct_hook=structure_channel_output),
)

converter.register_structure_hook(Advance, advance_structure_hook)

# Workaround for https://github.com/python-attrs/cattrs/issues/430
delay_structure_hook = cattrs.gen.make_dict_structure_fn(
    Delay,
    converter,
    input_=cattrs.override(struct_hook=structure_channel_output),
)

converter.register_structure_hook(Delay, delay_structure_hook)

broaden_left_structure_hook = cattrs.gen.make_dict_structure_fn(
    BroadenLeft,
    converter,
    input_=cattrs.override(struct_hook=structure_channel_output),
)

converter.register_structure_hook(BroadenLeft, broaden_left_structure_hook)


def structure_default(data, _):
    # We need this custom structure hook, because in the past the default value of a
    # DeviceTrigger was a Constant and not any ChannelOutput.
    # In that case, the type of the default value was not serialized, so we need to
    # deal with this special case.
    if data is None:
        return None
    if "type" in data:
        return converter.structure(data, ChannelOutput)
    else:
        return converter.structure(data, Constant)


structure_device_trigger = make_dict_structure_fn(
    DeviceTrigger,
    converter,
    default=override(struct_hook=structure_default),
)


converter.register_structure_hook(DeviceTrigger, structure_device_trigger)


def structure_lane_default(default_data, _):
    # We need this custom structure hook, because in the past the default value of a
    # LaneValues was a Constant and not any ChannelOutput.
    # In that case, the type of the default value was not serialized, so we need to
    # deal with this special case.
    if default_data is None:
        return None
    elif isinstance(default_data, str):
        default_expression = converter.structure(default_data, Expression)
        return Constant(value=default_expression)
    elif "type" in default_data:
        return converter.structure(default_data, ChannelOutput)
    else:
        return converter.structure(default_data, Constant)


structure_lane_values = make_dict_structure_fn(
    LaneValues,
    converter,
    default=override(struct_hook=structure_lane_default),
)


def unstructure_lane_values(lane_values):
    return {
        "lane": lane_values.lane,
        "default": converter.unstructure(lane_values.default, Optional[ChannelOutput]),
    }


converter.register_structure_hook(LaneValues, structure_lane_values)
converter.register_unstructure_hook(LaneValues, unstructure_lane_values)


def union_strategy(union, converter):
    return cattrs.strategies.configure_tagged_union(union, converter, tag_name="type")


cattrs.strategies.include_subclasses(
    ChannelOutput, converter, union_strategy=union_strategy
)

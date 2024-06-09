from caqtus.utils import serialization
from ._channel_sources import (
    LaneValues,
    Constant,
    DeviceTrigger,
    ValueSource,
    is_value_source,
)
from .channel_output import ChannelOutput
from caqtus.device.sequencer.channel_commands.timinig._timing import (
    Advance,
    Delay,
    BroadenLeft,
)
from ._calibrated_analog_mapping import CalibratedAnalogMapping, TimeIndependentMapping

serialization.include_subclasses(
    ChannelOutput, union_strategy=serialization.strategies.include_type("type")
)

__all__ = [
    "ChannelOutput",
    "LaneValues",
    "DeviceTrigger",
    "Constant",
    "ValueSource",
    "is_value_source",
    "Advance",
    "Delay",
    "BroadenLeft",
    "CalibratedAnalogMapping",
    "TimeIndependentMapping",
]

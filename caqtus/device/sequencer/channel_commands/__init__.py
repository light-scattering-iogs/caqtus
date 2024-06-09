from caqtus.utils import serialization
from . import timing
from ._calibrated_analog_mapping import CalibratedAnalogMapping, TimeIndependentMapping
from ._channel_sources import (
    LaneValues,
    Constant,
    DeviceTrigger,
    ValueSource,
    is_value_source,
)
from .channel_output import ChannelOutput

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
    "CalibratedAnalogMapping",
    "TimeIndependentMapping",
]

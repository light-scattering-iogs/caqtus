from caqtus.utils import serialization
from ._calibrated_analog_mapping import CalibratedAnalogMapping, TimeIndependentMapping
from ._channel_sources import (
    LaneValues,
    DeviceTrigger,
    Constant,
    ValueSource,
    is_value_source,
)
from ._timing import Advance, Delay, BroadenLeft
from .channel_output import (
    ChannelOutput,
)
from .configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    AnalogChannelConfiguration,
    DigitalChannelConfiguration,
)

serialization.include_subclasses(
    ChannelOutput, union_strategy=serialization.strategies.include_type("type")
)

__all__ = [
    "SequencerConfiguration",
    "ChannelConfiguration",
    "ChannelOutput",
    "LaneValues",
    "DeviceTrigger",
    "Constant",
    "Advance",
    "Delay",
    "AnalogChannelConfiguration",
    "DigitalChannelConfiguration",
    "CalibratedAnalogMapping",
    "ValueSource",
    "is_value_source",
    "TimeIndependentMapping",
    "BroadenLeft",
]

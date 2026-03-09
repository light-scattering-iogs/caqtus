"""This module defines what can be output by a sequencer channel.

Classes that inherit from :class:`ChannelOutput` declare what should be output by a
channel.
They can be evaluated to a :class:`EvaluatedOutput` object, which contains the sequence
of values to output and their units.

A channel output can be dependent on another channel output.
This allows the user to build complex evaluation pipelines for what should be output
by a sequencer channel.
"""

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

__all__ = [
    "ChannelOutput",
    "LaneValues",
    "DeviceTrigger",
    "Constant",
    "ValueSource",
    "is_value_source",
    "CalibratedAnalogMapping",
    "TimeIndependentMapping",
    "timing",
]

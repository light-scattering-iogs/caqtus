from typing import TypeGuard

from ._constant import Constant
from ._device_trigger import DeviceTrigger
from ._lane_values import LaneValues
from .compile_analog_lane import compile_analog_lane

# A channel output object is said to be a source if it generates values y(t) = f(t)
# an has no input value x(t).
ValueSource = LaneValues | DeviceTrigger | Constant


def is_value_source(obj) -> TypeGuard[ValueSource]:
    return isinstance(obj, (LaneValues, DeviceTrigger, Constant))


__all__ = [
    "LaneValues",
    "DeviceTrigger",
    "Constant",
    "ValueSource",
    "is_value_source",
    "compile_analog_lane",
]

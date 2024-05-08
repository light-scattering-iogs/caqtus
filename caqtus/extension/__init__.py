"""This module contains components to configure the components to use for a given
experiment.

The module :mod:`caqtus.extension.custom` can be used to configure the experiment and
launch the different components of the framework.
It is meant to be the main entry point for an experiment.

The class :class:`DeviceExtension` can be used to specify a new type of device.

The class :class:`TimeLaneExtension` can be used to implement a new type time lane.
"""

from .device_extension import DeviceExtension
from .time_lane_extension import TimeLaneExtension
from . import custom

__all__ = ["DeviceExtension", "TimeLaneExtension", "custom"]

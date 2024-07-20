"""This module contains classes to configure the components to use for a given
experiment.

The class :class:`Experiment` can be used to register extensions for a specific setup.

The class :class:`DeviceExtension` can be used to specify a new type of device.

The class :class:`TimeLaneExtension` can be used to specify a new type of time lane.
"""

from ._experiment import Experiment
from .device_extension import DeviceExtension
from .time_lane_extension import TimeLaneExtension

__all__ = ["DeviceExtension", "TimeLaneExtension", "Experiment"]

"""This module acts as a registry for custom extensions to the caqtus package."""

from ._extension import register_device_extension, register_time_lane_extension

__all__ = ["register_device_extension", "register_time_lane_extension"]

from typing import NewType

from device.configuration import DeviceConfigurationAttrs
from device.name import DeviceName
from device.runtime import RuntimeDevice
from util import serialization

DeviceParameter = NewType("DeviceParameter", str)
device_configurations_converter = serialization.converters["json"]

__all__ = [
    "DeviceName",
    "DeviceParameter",
    "RuntimeDevice",
    "DeviceConfigurationAttrs",
    "device_configurations_converter",
]

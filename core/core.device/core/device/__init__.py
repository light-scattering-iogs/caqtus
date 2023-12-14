from typing import NewType

from device.configuration import DeviceConfigurationAttrs
from device.name import DeviceName
from device.runtime import RuntimeDevice

DeviceParameter = NewType("DeviceParameter", str)

__all__ = ["DeviceName", "DeviceParameter", "RuntimeDevice", "DeviceConfigurationAttrs"]

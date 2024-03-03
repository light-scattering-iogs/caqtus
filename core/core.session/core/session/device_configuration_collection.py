import abc
from collections.abc import MutableMapping

from core.device import DeviceName, DeviceConfigurationAttrs


class DeviceConfigurationCollection(
    MutableMapping[DeviceName, DeviceConfigurationAttrs], abc.ABC
):
    pass

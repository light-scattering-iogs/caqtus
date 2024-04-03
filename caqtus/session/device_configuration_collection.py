import abc
from collections.abc import MutableMapping

from caqtus.device import DeviceName, DeviceConfiguration


class DeviceConfigurationCollection(
    MutableMapping[DeviceName, DeviceConfiguration], abc.ABC
):
    pass

import abc
from collections.abc import MutableMapping

from caqtus.device import DeviceName, DeviceConfiguration


class DeviceConfigurationCollection(
    MutableMapping[DeviceName, DeviceConfiguration], abc.ABC
):
    """A collection of device configurations inside a session.

    This object behaves like a dictionary where the keys are the names of the devices
    and the values are the configurations of the devices.
    """

    pass

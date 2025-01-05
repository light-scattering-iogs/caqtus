import abc
from collections.abc import MutableMapping
from typing import Optional

from caqtus.device import DeviceName, DeviceConfiguration
from caqtus.device.configuration import DeviceServerName


class DeviceConfigurationCollection(
    MutableMapping[DeviceName, DeviceConfiguration], abc.ABC
):
    """A collection of device configurations inside a session.

    This object behaves like a dictionary where the keys are the names of the devices
    and the values are the configurations of the devices.
    """

    @abc.abstractmethod
    def get_device_server(self, device_name: DeviceName) -> Optional[DeviceServerName]:
        """Get the name of the device server on which the device will be instantiated.

        Args:
            device_name: The name of the device.

        Raises:
            KeyError: If the device is not found.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def set_device_server(
        self, device_name: DeviceName, server_name: Optional[DeviceServerName]
    ) -> None:
        """Set the name of the device server on which the device will be instantiated.

        Args:
            device_name: The name of the device.
            server_name: The name of the device server.

        Raises:
            KeyError: If the device is not found.
        """

        raise NotImplementedError

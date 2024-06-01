from typing import Protocol

from caqtus.device import DeviceConfiguration, Device
from caqtus.device.configuration import DeviceServerName
from caqtus.device.controller import DeviceController
from caqtus.device.remote_server import DeviceServerConfiguration
from caqtus.shot_compilation import DeviceCompiler


class DeviceManagerExtensionProtocol(Protocol):
    def get_device_compiler_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceCompiler]: ...

    def get_device_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[Device]: ...

    def get_device_controller_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceController]: ...

    def get_device_server_config(
        self, server: DeviceServerName
    ) -> DeviceServerConfiguration:
        """Returns the configuration for the given device server.

        raises:
            KeyError: If no configuration is found for the given device server.
        """

        ...

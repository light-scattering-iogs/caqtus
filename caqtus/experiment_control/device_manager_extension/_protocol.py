from collections.abc import Callable
from typing import Protocol

from caqtus.device import DeviceConfiguration, Device
from caqtus.device.configuration import DeviceServerName
from caqtus.device.controller import DeviceController
from caqtus.device.remote import DeviceProxy, RPCConfiguration
from caqtus.shot_compilation import DeviceCompiler


class DeviceManagerExtensionProtocol(Protocol):
    def get_device_compiler_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceCompiler]: ...

    def get_device_type(
        self, device_configuration: DeviceConfiguration
    ) -> Callable[..., Device]: ...

    def get_device_controller_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceController]: ...

    def get_proxy_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceProxy]:
        """Returns the type used to create proxies for the given device configuration."""

        ...

    def get_device_server_config(self, server: DeviceServerName) -> RPCConfiguration:
        """Returns the configuration for the given device server.

        raises:
            KeyError: If no configuration is found for the given device server.
        """

        ...

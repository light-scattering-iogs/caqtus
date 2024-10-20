from collections.abc import Callable

from caqtus.device import DeviceConfiguration, Device, DeviceController
from caqtus.device.configuration import DeviceServerName
from caqtus.device.remote import DeviceProxy, RPCConfiguration
from caqtus.shot_compilation import DeviceCompiler
from ._protocol import DeviceManagerExtensionProtocol


class DeviceManagerExtension(DeviceManagerExtensionProtocol):
    def __init__(self):
        self._compiler_types: dict[type[DeviceConfiguration], type[DeviceCompiler]] = {}
        self._device_types: dict[type[DeviceConfiguration], Callable[..., Device]] = {}
        self._controller_types: dict[
            type[DeviceConfiguration], type[DeviceController]
        ] = {}
        self._proxy_types: dict[type[DeviceConfiguration], type[DeviceProxy]] = {}
        self._device_server_configs: dict[DeviceServerName, RPCConfiguration] = {}

    def register_device_compiler(
        self,
        configuration_type: type[DeviceConfiguration],
        compiler_type: type[DeviceCompiler],
    ) -> None:
        self._compiler_types[configuration_type] = compiler_type

    def register_device[
        D: Device
    ](
        self,
        configuration_type: type[DeviceConfiguration[D]],
        device_type: Callable[..., D],
    ) -> None:
        self._device_types[configuration_type] = device_type

    def register_controller(
        self,
        configuration_type: type[DeviceConfiguration],
        controller_type: type[DeviceController],
    ) -> None:
        self._controller_types[configuration_type] = controller_type

    def register_proxy(
        self,
        configuration_type: type[DeviceConfiguration],
        proxy_type: type[DeviceProxy],
    ) -> None:
        self._proxy_types[configuration_type] = proxy_type

    def register_device_server_config(
        self,
        name: DeviceServerName,
        config: RPCConfiguration,
    ) -> None:
        self._device_server_configs[name] = config

    def get_device_compiler_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceCompiler]:
        return self._compiler_types[type(device_configuration)]

    def get_device_type(
        self, device_configuration: DeviceConfiguration
    ) -> Callable[..., Device]:
        return self._device_types[type(device_configuration)]

    def get_device_controller_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceController]:
        return self._controller_types[type(device_configuration)]

    def get_proxy_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceProxy]:
        return self._proxy_types[type(device_configuration)]

    def get_device_server_config(self, server: DeviceServerName) -> RPCConfiguration:
        return self._device_server_configs[server]

from ._protocol import DeviceManagerExtensionProtocol
from ...device import DeviceConfiguration, Device
from ...device.controller import DeviceController
from ...shot_compilation import DeviceCompiler


class DeviceManagerExtension(DeviceManagerExtensionProtocol):
    def __init__(self):
        self._compiler_types: dict[type[DeviceConfiguration], type[DeviceCompiler]] = {}
        self._device_types: dict[type[DeviceConfiguration], type[Device]] = {}
        self._controller_types: dict[
            type[DeviceConfiguration], type[DeviceController]
        ] = {}

    def register_device_compiler(
        self,
        configuration_type: type[DeviceConfiguration],
        compiler_type: type[DeviceCompiler],
    ) -> None:
        self._compiler_types[configuration_type] = compiler_type

    def register_device(
        self,
        configuration_type: type[DeviceConfiguration],
        device_type: type[Device],
    ) -> None:
        self._device_types[configuration_type] = device_type

    def register_controller(
        self,
        configuration_type: type[DeviceConfiguration],
        controller_type: type[DeviceController],
    ) -> None:
        self._controller_types[configuration_type] = controller_type

    def get_device_compiler_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceCompiler]:
        return self._compiler_types[type(device_configuration)]

    def get_device_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[Device]:
        return self._device_types[type(device_configuration)]

    def get_device_controller_type(
        self, device_configuration: DeviceConfiguration
    ) -> type[DeviceController]:
        return self._controller_types[type(device_configuration)]

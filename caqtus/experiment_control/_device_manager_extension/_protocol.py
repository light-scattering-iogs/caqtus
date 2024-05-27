from typing import Protocol

from caqtus.device import DeviceConfiguration, Device
from caqtus.device.controller import DeviceController
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

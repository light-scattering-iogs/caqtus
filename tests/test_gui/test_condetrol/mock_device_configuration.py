from typing import Any, Mapping

from caqtus.device import DeviceConfiguration, DeviceName
from caqtus.shot_compilation import ShotContext


class MockDeviceConfiguration(DeviceConfiguration):
    def compile_device_shot_parameters(
        self, device_name: DeviceName, shot_context: ShotContext
    ) -> Mapping[str, Any]:
        pass

    def get_device_initialization_method(self, device_name, sequence_context):
        raise NotImplementedError

from typing import Any, Mapping

from caqtus.device import DeviceConfiguration, DeviceParameter, DeviceName
from caqtus.shot_compilation import ShotContext


class MockDeviceConfiguration(DeviceConfiguration):
    def compile_device_shot_parameters(
        self, device_name: DeviceName, shot_context: ShotContext
    ) -> Mapping[str, Any]:
        pass

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        raise NotImplementedError

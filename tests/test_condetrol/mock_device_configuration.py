from typing import Any

from caqtus.device import DeviceConfigurationAttrs, DeviceParameter


class MockDeviceConfiguration(DeviceConfigurationAttrs):
    def get_device_type(self) -> str:
        raise NotImplementedError

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        raise NotImplementedError

from typing import Mapping, Any

from caqtus.device import Device, DeviceConfiguration, DeviceParameter, DeviceName
from caqtus.shot_compilation import ShotContext


class DeviceTest(Device):
    pass


class DeviceTestConfiguration(DeviceConfiguration[DeviceTest]):
    def compile_device_shot_parameters(
        self, device_name: DeviceName, shot_context: ShotContext
    ) -> Mapping[str, Any]:
        pass

    def get_device_init_args(self, *args, **kwargs) -> Mapping[DeviceParameter, Any]:
        pass


def test():
    assert DeviceTestConfiguration(remote_server=None).get_device_type() == DeviceTest


class DeviceTestConfiguration1(DeviceConfiguration["DeviceTest"]):
    def compile_device_shot_parameters(
        self, device_name: DeviceName, shot_context: "ShotContext"
    ) -> Mapping[str, Any]:
        pass

    def get_device_init_args(self, *args, **kwargs) -> Mapping[DeviceParameter, Any]:
        pass


def test1():
    assert (
        DeviceTestConfiguration1(remote_server=None).get_device_type() == "DeviceTest"
    )

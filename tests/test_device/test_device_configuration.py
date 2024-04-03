from typing import Mapping, Any

from caqtus.device import Device, DeviceConfiguration, DeviceParameter


class DeviceTest(Device):
    pass


class DeviceTestConfiguration(DeviceConfiguration[DeviceTest]):
    def get_device_init_args(self, *args, **kwargs) -> Mapping[DeviceParameter, Any]:
        pass

    def compile_shot_parameters(self):
        pass


def test():
    assert DeviceTestConfiguration(remote_server=None).get_device_type() == "DeviceTest"


class DeviceTestConfiguration1(DeviceConfiguration["DeviceTest"]):
    def get_device_init_args(self, *args, **kwargs) -> Mapping[DeviceParameter, Any]:
        pass

    def compile_shot_parameters(self):
        pass


def test1():
    assert (
        DeviceTestConfiguration1(remote_server=None).get_device_type() == "DeviceTest"
    )

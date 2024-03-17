import os
from typing import Self

from core.device import Device, DeviceName
from core.device.remote_server import RemoteDeviceManager, DeviceProxy


class DeviceTest(Device):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = DeviceName(name)

    def get_name(self) -> DeviceName:
        return self.name

    def __enter__(self) -> Self:
        print("Entering device")
        return self

    def update_parameters(self, *_, **kwargs) -> None:
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting device")

    def __repr__(self):
        return f"DeviceTest({self.name}, pid={os.getpid()})"

    def __getstate__(self):
        raise Exception("This object cannot be pickled")


class Manager(RemoteDeviceManager):
    pass


Manager.register_device(DeviceTest, DeviceProxy)


def test():
    print(os.getpid())
    with Manager() as m:
        device = m.DeviceTest("test_device")
        print(str(device))
        assert isinstance(device, DeviceProxy)
        with device as d:
            assert d.get_name() == "test_device"

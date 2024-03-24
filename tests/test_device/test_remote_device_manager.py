import os
import time
from typing import Self

from caqtus.device import Device, DeviceName
from caqtus.device.camera import Camera
from caqtus.device.remote_server import (
    RemoteDeviceManager,
    DeviceProxy,
    CameraProxy,
    SequencerProxy,
)
from caqtus.device.sequencer import Sequencer
from caqtus.device.sequencer.instructions import SequencerInstruction
from caqtus.types.image import Image
from caqtus.utils.roi import RectangularROI


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


class CameraTest(Camera):
    sensor_width = 100
    sensor_height = 100

    def _read_image(self, exposure: float) -> Image:
        pass

    def _stop_acquisition(self) -> None:
        pass

    def _start_acquisition(self, exposures: list[float]) -> None:
        pass

    def update_parameters(self, timeout: float) -> None:
        pass


class SequencerTest(Sequencer):
    def update_parameters(self, *_, sequence: SequencerInstruction, **kwargs) -> None:
        pass

    def start_sequence(self) -> None:
        pass

    def has_sequence_finished(self) -> bool:
        pass


class T1(DeviceTest):
    def method_1(self):
        return "method 1"


class T2(DeviceTest):
    def method_2(self):
        return "method 2"


class T1Proxy(DeviceProxy):
    _exposed_ = DeviceProxy._exposed_ + ("method_1",)

    def method_1(self):
        return self._callmethod("method_1")


class T2Proxy(DeviceProxy):
    _exposed_ = DeviceProxy._exposed_ + ("method_2",)

    def method_2(self):
        return self._callmethod("method_2")


class Manager(RemoteDeviceManager):
    pass


Manager.register_device(DeviceTest, DeviceProxy)
Manager.register_device(T1, T1Proxy)
Manager.register_device(T2, T2Proxy)
Manager.register_device(CameraTest, CameraProxy)
Manager.register_device(SequencerTest, SequencerProxy)
Manager.register_device(SequencerTest, SequencerProxy)


def test_0():
    print(os.getpid())
    with Manager() as m:
        device = m.DeviceTest("test_device")
        print(str(device))
        assert isinstance(device, DeviceProxy)
        with device as d:
            assert d.get_name() == "test_device"


def test_1():
    with Manager() as m:
        dev1 = m.T1("test_device")
        dev2 = m.T2("test_device")

        assert dev1.method_1() == "method 1"
        assert dev2.method_2() == "method 2"


def test_2():
    with Manager() as m:
        cam = m.CameraTest(
            timeout=1,
            external_trigger=False,
            roi=RectangularROI((100, 100), 0, 100, 0, 100),
        )
        with cam:
            print(f"entering at {time.time()}")
            with cam.acquire([0.1, 0.2, 0.3]) as images:
                for image in images:
                    pass

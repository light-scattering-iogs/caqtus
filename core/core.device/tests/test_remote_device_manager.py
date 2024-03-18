import contextlib
import os
from typing import Self, Iterable

from core.device import Device, DeviceName
from core.device.camera import Camera
from core.device.remote_server import RemoteDeviceManager, DeviceProxy, CameraProxy, \
    SequencerProxy
from core.device.sequencer import Sequencer
from core.device.sequencer.instructions import SequencerInstruction
from core.types.image import Image
from util.roi import RectangularROI


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


class TestCamera(Camera):
    sensor_width = 100
    sensor_height = 100

    @contextlib.contextmanager
    def acquire(
        self, exposures: list[float]
    ) -> contextlib.AbstractContextManager[Iterable[Image]]:
        yield self.yield_images(exposures)

    def yield_images(self, exposures: list[float]) -> Iterable[Image]:
        for _ in range(len(exposures)):
            yield None

    def update_parameters(self, timeout: float) -> None:
        pass


class TestSequencer(Sequencer):
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
Manager.register_device(TestCamera, CameraProxy)
Manager.register_device(TestSequencer, SequencerProxy)
Manager.register_device(TestSequencer, SequencerProxy)


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
        cam = m.TestCamera(
            timeout=1,
            external_trigger=False,
            roi=RectangularROI((100, 100), 0, 100, 0, 100),
        )
        with cam:
            with cam.acquire([0.1, 0.2, 0.3]) as images:
                for image in images:
                    pass


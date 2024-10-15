import contextlib
import copyreg
from collections.abc import AsyncGenerator

import anyio
import anyio.lowlevel
import anyio.to_thread
import numpy as np
import pytest

from caqtus.device import Device
from caqtus.device.camera import Camera, CameraProxy
from caqtus.device.remote import DeviceProxy
from caqtus.device.remote.rpc import RPCServer, RPCClient
from caqtus.types.image import Image


class CustomError(Exception):
    def __init__(self, msg: str, error_code: int):
        super().__init__(msg)
        self.error_code = error_code


class DeviceMock(Device):
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        print("enter")
        return self

    def will_raise(self):
        raise ValueError("test")

    def raise_custom_exception(self):
        raise CustomError("test", 42)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            print(f"exit with exception {exc_value}")
            return
        else:
            print("exit")
            return False


@pytest.fixture()
def anyio_backend():
    return "trio"


@contextlib.asynccontextmanager
async def run_server() -> AsyncGenerator[RPCServer, None]:
    with RPCServer(12345) as server, anyio.CancelScope() as scope:
        async with anyio.create_task_group() as tg:
            tg.start_soon(server.run_async)
            try:
                yield server
            finally:
                scope.cancel()


async def test_0(anyio_backend, capsys):
    async with run_server() as server:
        async with (
            RPCClient("localhost", server.port) as client,
            DeviceProxy(client, DeviceMock, "test") as device,
        ):
            assert await device.get_attribute("name") == "test"
            with pytest.raises(ValueError):
                await device.call_method("will_raise")

    captured = capsys.readouterr()

    assert captured.out == "enter\nexit\n"


async def test_exception_inside_sequence_reraised(anyio_backend, capsys):
    async with run_server() as server:
        with pytest.raises(ValueError):
            async with (
                RPCClient("localhost", server.port) as client,
                DeviceProxy(client, DeviceMock, "test"),
            ):
                raise ValueError("test")

    captured = capsys.readouterr()

    assert captured.out == "enter\nexit with exception test\n"


async def test_cancelled_exception_handled(anyio_backend, capsys):
    async with run_server() as server:
        with anyio.CancelScope() as scope:
            async with (
                RPCClient("localhost", server.port) as client,
                DeviceProxy(client, DeviceMock, "test"),
            ):
                scope.cancel()
                await anyio.lowlevel.checkpoint()
        assert scope.cancel_called


def pickle_custom_exception(obj):
    return CustomError, (obj.args, obj.error_code)


async def test_custom_exception(anyio_backend):
    copyreg.pickle(CustomError, pickle_custom_exception)
    async with run_server() as server:
        async with (
            RPCClient("localhost", server.port) as client,
            DeviceProxy(client, DeviceMock, "test") as device,
        ):
            try:
                await device.call_method("raise_custom_exception")
            except CustomError as e:
                assert e.error_code == 42
            else:
                raise AssertionError("CustomException not raised")


class MockCamera(Camera):
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def update_parameters(self, timeout: float, *args, **kwargs) -> None:
        pass

    @contextlib.contextmanager
    def acquire(self, exposures: list[float]):
        self._start_acquisition(exposures)
        try:
            yield (self._read_image(exposure) for exposure in exposures)
        finally:
            self._stop_acquisition()

    def _start_acquisition(self, exposures: list[float]) -> None:
        print("start acquisition")

    def _read_image(self, exposure: float) -> Image:
        return np.array([[0, 1], [2, 3]]) * exposure

    def _stop_acquisition(self) -> None:
        print("stop acquisition")


async def test_camera(anyio_backend, capsys):
    images = []
    async with run_server() as server:
        async with (
            RPCClient("localhost", server.port) as client,
            CameraProxy(client, MockCamera, "test") as camera,
        ):
            async with camera.acquire([1, 2]) as image_stream:
                async for image in image_stream:
                    images.append(image)

    captured = capsys.readouterr()

    assert captured.out == "start acquisition\nstop acquisition\n"
    assert np.allclose(images, [np.array([[0, 1], [2, 3]]), np.array([[0, 2], [4, 6]])])

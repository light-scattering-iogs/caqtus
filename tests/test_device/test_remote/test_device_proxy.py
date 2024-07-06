import contextlib

import anyio
import anyio.to_thread
import numpy as np
import pytest

from caqtus.device import Device
from caqtus.device.camera import Camera, CameraProxy
from caqtus.device.remote import DeviceProxy
from caqtus.device.remote.rpc import RPCServer, RPCClient
from caqtus.types.image import Image


class DeviceMock(Device):
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        print("enter")
        return self

    def will_raise(self):
        raise ValueError("test")

    def __exit__(self, exc_type, exc_value, traceback):
        print("exit")
        return False


@pytest.fixture()
def anyio_backend():
    return "trio"


async def run_server(scope: anyio.CancelScope, task_status):
    with RPCServer(12345) as server, scope:
        task_status.started()
        await server.run_async()


async def test_0(anyio_backend, capsys):
    server_scope = anyio.CancelScope()

    async def run_client():
        async with (
            RPCClient("localhost", 12345) as client,
            DeviceProxy(client, DeviceMock, "test") as device,
        ):
            assert await device.get_attribute("name") == "test"
            with pytest.raises(ValueError):
                await device.call_method("will_raise")
        server_scope.cancel()

    async with anyio.create_task_group() as tg:
        await tg.start(run_server, server_scope)
        tg.start_soon(run_client)

    captured = capsys.readouterr()

    assert captured.out == "enter\nexit\n"


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
    server_scope = anyio.CancelScope()

    images = []

    async def run_client():
        async with (
            RPCClient("localhost", 12345) as client,
            CameraProxy(client, MockCamera, "test") as camera,
        ):
            async with camera.acquire([1, 2]) as image_stream:
                async for image in image_stream:
                    images.append(image)

        server_scope.cancel()

    async with anyio.create_task_group() as tg:
        await tg.start(run_server, server_scope)
        tg.start_soon(run_client)

    captured = capsys.readouterr()

    assert captured.out == "start acquisition\nstop acquisition\n"
    assert np.allclose(images, [np.array([[0, 1], [2, 3]]), np.array([[0, 2], [4, 6]])])

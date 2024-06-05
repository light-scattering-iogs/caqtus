import contextlib
from multiprocessing import Process, Event

import anyio
import grpc
import numpy as np
import pytest

from caqtus.device import Device
from caqtus.device.camera import Camera, CameraProxy
from caqtus.device.remote import (
    DeviceProxy,
    SecureRPCConfiguration,
    LocalRPCCredentials,
)
from caqtus.device.remote.rpc import Server, Client
from caqtus.device.remote.rpc.proxy import Proxy
from caqtus.types.image import Image
from caqtus.utils.roi import RectangularROI


def _run_server(e):
    with Server(
        SecureRPCConfiguration(
            target="[::]:50051",
            credentials=LocalRPCCredentials(grpc.LocalConnectionType.LOCAL_TCP),
        )
    ):
        e.wait()


@contextlib.contextmanager
def run_server():
    e = Event()
    p = Process(target=_run_server, args=(e,))
    p.start()
    try:
        yield
    finally:
        e.set()
        p.join()


def create_client():
    return Client(
        SecureRPCConfiguration(
            target="localhost:50051",
            credentials=LocalRPCCredentials(grpc.LocalConnectionType.LOCAL_TCP),
        )
    )


def test_1():
    async def fun():
        async with create_client() as client, client.call_proxy_result(
            list, [1, 2, 3]
        ) as l:
            assert isinstance(l, Proxy)
            await client.call_method(l, "append", 4)
            assert await client.call(len, l) == 4

    with run_server():
        anyio.run(fun)


def test_2():
    async def fun():
        async with create_client() as client, client.call_proxy_result(list, [1, 2, 3]):
            raise RuntimeError("This is a test")

    with run_server(), pytest.raises(RuntimeError):
        anyio.run(fun)


class DeviceMock(Device):
    def __init__(self):
        super().__init__()
        self.state = 0

    def __enter__(self):
        self.state = 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.state = 2
        return False


def test_3():
    async def fun():
        async with create_client() as client, DeviceProxy(client, DeviceMock) as device:
            assert await device.get_attribute("state") == 1

    with run_server():
        anyio.run(fun)


class CameraMock(Camera):
    sensor_width = 100
    sensor_height = 100

    def _start_acquisition(self, exposures: list[float]) -> None:
        pass

    def _read_image(self, exposure: float) -> Image:
        return np.array([[1, 2, 3]])

    def _stop_acquisition(self) -> None:
        pass

    def update_parameters(self, timeout: float, *args, **kwargs) -> None:
        pass


def test_4():
    async def fun():
        async with create_client() as client, CameraProxy(
            client,
            CameraMock,
            roi=RectangularROI(
                original_image_size=(100, 100), x=0, y=0, width=100, height=100
            ),
            timeout=1,
            external_trigger=True,
        ) as camera:
            async with camera.acquire([1.0, 1.0, 1.0]) as images:
                async for image in images:
                    assert np.all(image == np.array([[1, 2, 3]]))

    with run_server():
        anyio.run(fun)

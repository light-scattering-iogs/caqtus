import contextlib
from multiprocessing import Process, Event

import anyio
import pytest

from caqtus.device import Device
from caqtus.device.remote import DeviceProxy
from caqtus.device.remote.rpc import Server, Client
from caqtus.device.remote.rpc.proxy import Proxy


def _run_server(e):
    with Server():
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


def test_1():
    async def fun():
        async with Client("localhost:50051") as client, client.call_proxy_result(
            list, [1, 2, 3]
        ) as l:
            assert isinstance(l, Proxy)
            await client.call_method(l, "append", 4)
            assert await client.call(len, l) == 4

    with run_server():
        anyio.run(fun)


def test_2():
    async def fun():
        async with Client("localhost:50051") as client, client.call_proxy_result(
            list, [1, 2, 3]
        ):
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
        async with Client("localhost:50051") as client:
            async with DeviceProxy(client, DeviceMock) as device:
                assert await device.get_attribute("state") == 1
            assert await device.get_attribute("state") == 2

    with run_server():
        anyio.run(fun)

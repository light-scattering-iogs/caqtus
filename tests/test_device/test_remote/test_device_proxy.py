import anyio
import pytest

from caqtus.device import Device
from caqtus.device.remote import DeviceProxy
from caqtus.device.remote.rpc import RPCServer, RPCClient


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

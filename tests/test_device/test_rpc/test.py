import asyncio
import contextlib
from multiprocessing import Process, Event

from caqtus.device.remote.rpc import Server, Client


def _run_server(e):
    with Server() as server:
        e.wait()


@contextlib.contextmanager
def run_server():
    e = Event()
    p = Process(target=_run_server, args=(e,))
    p.start()
    yield
    e.set()
    p.join()


def test_1():
    async def fun():
        async with Client("localhost:50051") as client:
            l = await client.call(list, [1, 2, 3], result="proxy")
            await client.call(list.append, l, 4)
            assert await client.call(len, l) == 4

    with run_server():
        asyncio.run(fun())

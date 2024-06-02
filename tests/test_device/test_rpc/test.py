import asyncio
import contextlib
import os
from multiprocessing import Process, Event

from caqtus.device.remote.rpc import Server, Client


def _run_server(e):
    with Server() as server:
        with open("server.pid", "w") as f:
            f.write(str(os.getpid()))
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
        async with Client("localhost:50051") as client:
            l = await client.call(list, [1, 2, 3], returned_value="proxy")
            await client.call_method(l, "append", 4)
            assert await client.call(len, l) == 4

    with run_server():
        asyncio.run(fun())

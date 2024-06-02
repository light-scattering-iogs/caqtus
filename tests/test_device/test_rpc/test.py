import contextlib
import os
from multiprocessing import Process, Event

import anyio

from caqtus.device.remote.rpc import Server, Client
from caqtus.device.remote.rpc.proxy import Proxy


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
        async with Client("localhost:50051") as client, client.call_proxy_result(
            list, [1, 2, 3]
        ) as l:
            assert isinstance(l, Proxy)
            await client.call_method(l, "append", 4)
            assert await client.call(len, l) == 4

    with run_server():
        anyio.run(fun)

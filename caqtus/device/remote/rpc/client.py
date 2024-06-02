import contextlib
import pickle
from typing import Callable, TypeVar, ParamSpec, Self, Literal

import grpc
import grpc.aio

from . import rpc_pb2
from . import rpc_pb2_grpc
from .proxy import Proxy

P = ParamSpec("P")
T = TypeVar("T")


class Client:
    """

    Args:
        target: The server address to connect to.
    """

    def __init__(self, target: str):
        self._async_channel = grpc.aio.insecure_channel(target)
        self._sync_channel = grpc.insecure_channel(target)
        self._stub = rpc_pb2_grpc.RemoteCallStub(self._async_channel)

        self._exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> Self:
        await self._exit_stack.__aenter__()
        await self._exit_stack.enter_async_context(self._async_channel)
        self._exit_stack.enter_context(self._sync_channel)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def call(
        self,
        fun: Callable[P, T],
        *args: P.args,
        result: Literal["serialized", "proxy"] = "serialized",
        **kwargs: P.kwargs,
    ) -> T | Proxy[T]:
        response = await self._stub.Call(
            rpc_pb2.CallRequest(
                function=pickle.dumps(fun),
                args=[pickle.dumps(arg) for arg in args],
                kwargs={key: pickle.dumps(value) for key, value in kwargs.items()},
                return_value=(
                    rpc_pb2.ReturnValue.SERIALIZED
                    if result == "serialized"
                    else rpc_pb2.ReturnValue.PROXY
                ),
            )
        )

        return_type = response.WhichOneof("result")
        if return_type == "success":
            return pickle.loads(response.success)
        elif return_type == "failure":
            raise pickle.loads(response.failure)
        else:
            assert False, f"Unknown return type: {return_type}"

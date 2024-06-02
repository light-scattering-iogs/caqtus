import contextlib
import operator
import pickle
from typing import (
    Callable,
    TypeVar,
    ParamSpec,
    Self,
    Literal,
    TypeAlias,
    LiteralString,
    Any,
)

import grpc
import grpc.aio
import tblib.pickling_support

from . import rpc_pb2
from . import rpc_pb2_grpc
from .proxy import Proxy

tblib.pickling_support.install()

P = ParamSpec("P")
T = TypeVar("T")

ReturnedType: TypeAlias = Literal["copy", "proxy"]


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

    async def call_method(
        self,
        obj: Any,
        method: LiteralString,
        *args: Any,
        returned_value: ReturnedType = "copy",
        **kwargs: Any,
    ) -> Any:
        caller = operator.methodcaller(method, *args, **kwargs)
        return await self.call(caller, obj, returned_value=returned_value)

    async def call(
        self,
        fun: Callable[P, T],
        *args: P.args,
        returned_value: ReturnedType = "copy",
        **kwargs: P.kwargs,
    ) -> T | Proxy[T]:
        response = await self._stub.Call(
            rpc_pb2.CallRequest(
                function=pickle.dumps(fun),
                args=[pickle.dumps(arg) for arg in args],
                kwargs={key: pickle.dumps(value) for key, value in kwargs.items()},
                return_value=(
                    rpc_pb2.ReturnValue.SERIALIZED
                    if returned_value == "copy"
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

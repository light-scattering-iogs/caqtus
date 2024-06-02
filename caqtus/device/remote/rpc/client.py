import contextlib
import operator
import pickle
from collections.abc import AsyncGenerator
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
        self._stub = rpc_pb2_grpc.RemoteCallStub(self._async_channel)

        self._exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> Self:
        await self._exit_stack.__aenter__()
        await self._exit_stack.enter_async_context(self._async_channel)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def call_method(
        self,
        obj: Any,
        method: LiteralString,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        caller = operator.methodcaller(method, *args, **kwargs)
        return await self.call(caller, obj)

    async def call(
        self,
        fun: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        response = await self._stub.Call(self._build_request(fun, args, kwargs, "copy"))
        return self._build_result(response)

    @contextlib.asynccontextmanager
    async def call_proxy_result(
        self, fun: Callable[..., T], *args: Any, **kwargs: Any
    ) -> AsyncGenerator[Proxy[T], None]:
        response = await self._stub.Call(
            self._build_request(fun, args, kwargs, "proxy")
        )
        proxy = self._build_result(response)
        assert isinstance(proxy, Proxy)
        try:
            yield proxy
        finally:
            await self._close_proxy(proxy)

    async def _close_proxy(self, proxy: Proxy[T]) -> None:
        pass

    @staticmethod
    def _build_request(
        fun: Callable[..., T], args: Any, kwargs: Any, returned_value: ReturnedType
    ) -> rpc_pb2.CallRequest:
        return rpc_pb2.CallRequest(
            function=pickle.dumps(fun),
            args=[pickle.dumps(arg) for arg in args],
            kwargs={key: pickle.dumps(value) for key, value in kwargs.items()},
            return_value=(
                rpc_pb2.ReturnValue.SERIALIZED
                if returned_value == "copy"
                else rpc_pb2.ReturnValue.PROXY
            ),
        )

    @staticmethod
    def _build_result(response: rpc_pb2.CallResponse) -> Any:
        return_type = response.WhichOneof("result")
        if return_type == "success":
            return pickle.loads(response.success)
        elif return_type == "failure":
            raise pickle.loads(response.failure)
        else:
            assert False, f"Unknown return type: {return_type}"

import contextlib
import operator
import pickle
from collections.abc import AsyncGenerator, Iterator, AsyncIterator
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

import anyio
import grpc
import grpc.aio
import tblib.pickling_support

from . import rpc_pb2
from . import rpc_pb2_grpc
from ._configuration import (
    SecureRPCConfiguration,
    RPCConfiguration,
)
from .proxy import Proxy
from .server import RemoteError

tblib.pickling_support.install()

P = ParamSpec("P")
T = TypeVar("T")

ReturnedType: TypeAlias = Literal["copy", "proxy"]


class Client:
    """A client to call remote functions running on a server.

    Args:
        target: The server address to connect to.
        credentials: The credentials to use for the connection.
    """

    def __init__(self, config: RPCConfiguration) -> None:
        if isinstance(config, SecureRPCConfiguration):
            credentials = config.credentials.get_credentials()
            self._async_channel = grpc.aio.secure_channel(
                config.target, credentials=credentials
            )
        else:
            self._async_channel = grpc.aio.insecure_channel(config.target)
        self._stub = rpc_pb2_grpc.RemoteCallStub(self._async_channel)

    async def __aenter__(self) -> Self:
        await self._async_channel.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        with anyio.CancelScope(shield=True):
            await self._async_channel.__aexit__(exc_type, exc_value, traceback)

    async def call_method(
        self,
        obj: Any,
        method: LiteralString,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        caller = operator.methodcaller(method, *args, **kwargs)
        return await self.call(caller, obj)

    @contextlib.asynccontextmanager
    async def call_method_proxy_result(
        self,
        obj: Any,
        method: LiteralString,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        caller = operator.methodcaller(method, *args, **kwargs)
        async with self.call_proxy_result(caller, obj) as result:
            yield result

    async def get_attribute(self, obj: Any, attribute: LiteralString) -> Any:
        caller = operator.attrgetter(attribute)
        return await self.call(caller, obj)

    async def call(
        self,
        fun: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        with anyio.CancelScope(shield=True):
            response = await self._stub.Call(
                self._build_request(fun, args, kwargs, "copy")
            )
        return self._build_result(response)

    @contextlib.asynccontextmanager
    async def call_proxy_result(
        self, fun: Callable[..., T], *args: Any, **kwargs: Any
    ) -> AsyncGenerator[Proxy[T], None]:
        with anyio.CancelScope(shield=True):
            response = await self._stub.Call(
                self._build_request(fun, args, kwargs, "proxy")
            )
            proxy = self._build_result(response)
            assert isinstance(proxy, Proxy)
            try:
                yield proxy
            finally:
                await self._close_proxy(proxy)

    @contextlib.asynccontextmanager
    async def async_context_manager(
        self, proxy: Proxy[contextlib.AbstractContextManager[T]]
    ) -> AsyncGenerator[Proxy[T], None]:
        try:
            async with self.call_method_proxy_result(proxy, "__enter__") as result:
                yield result
        finally:
            with anyio.CancelScope(shield=True):
                await self.call_method(proxy, "__exit__", None, None, None)

    async def async_iterator(self, proxy: Proxy[Iterator[T]]) -> AsyncIterator[T]:
        while True:
            try:
                value = await self.call_method(proxy, "__next__")
                yield value
            except RemoteError as error:
                if isinstance(error.__cause__, StopIteration):
                    break
                else:
                    raise

    async def _close_proxy(self, proxy: Proxy[T]) -> None:
        await self._stub.DeleteReferent(
            rpc_pb2.DeleteReferentRequest(proxy=pickle.dumps(proxy))
        )

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

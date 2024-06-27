import contextlib
import operator
import pickle
from collections.abc import Callable, AsyncGenerator, Iterator, AsyncIterator
from typing import Any, TypeVar, TypeAlias, Literal, LiteralString

import anyio

from ._prefix_size import receive_with_size_prefix, send_with_size_prefix
from ._server import (
    CallRequest,
    ReturnValue,
    CallResponse,
    CallResponseSuccess,
    CallResponseFailure,
    DeleteProxyRequest,
)
from .proxy import Proxy
from .server import RemoteError

T = TypeVar("T")

ReturnedType: TypeAlias = Literal["copy", "proxy"]


class RPCClient:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

    async def __aenter__(self):
        self._stream = await anyio.connect_tcp(self._host, self._port)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._stream.__aexit__(exc_type, exc_value, traceback)

    async def call(
        self,
        fun: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        request = self._build_request(fun, args, kwargs, "copy")
        pickled = pickle.dumps(request)
        await send_with_size_prefix(self._stream, pickled)
        bytes_response = await receive_with_size_prefix(self._stream)
        response = pickle.loads(bytes_response)
        return self._build_result(response)

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

    @contextlib.asynccontextmanager
    async def call_proxy_result(
        self, fun: Callable[..., T], *args: Any, **kwargs: Any
    ) -> AsyncGenerator[Proxy[T], None]:

        request = self._build_request(fun, args, kwargs, "proxy")
        pickled_request = pickle.dumps(request)
        with anyio.CancelScope(shield=True):
            await send_with_size_prefix(self._stream, pickled_request)
            pickled_response = await receive_with_size_prefix(self._stream)
            response = pickle.loads(pickled_response)

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
        with anyio.CancelScope(shield=True):
            try:
                async with self.call_method_proxy_result(proxy, "__enter__") as result:
                    yield result
            finally:
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
        request = DeleteProxyRequest(proxy)
        pickled_request = pickle.dumps(request)
        await send_with_size_prefix(self._stream, pickled_request)

    @staticmethod
    def _build_request(
        fun: Callable[..., T], args: Any, kwargs: Any, returned_value: ReturnedType
    ) -> CallRequest:
        return CallRequest(
            function=fun,
            args=args,
            kwargs=kwargs,
            return_value=(
                ReturnValue.SERIALIZED
                if returned_value == "copy"
                else ReturnValue.PROXY
            ),
        )

    @staticmethod
    def _build_result(response: CallResponse) -> Any:
        match response:
            case CallResponseSuccess(result=result):
                return result
            case CallResponseFailure(error=error):
                raise error

import contextlib
import operator
import pickle
from collections.abc import Callable, AsyncGenerator, Iterator, AsyncIterator
from typing import Any, TypeVar, TypeAlias, Literal, LiteralString

import anyio
import attrs
import eliot
from anyio.streams.buffered import BufferedByteReceiveStream

from ._prefix_size import receive_with_size_prefix, send_with_size_prefix
from ._server import (
    CallRequest,
    ReturnValue,
    CallResponse,
    CallResponseSuccess,
    CallResponseFailure,
    DeleteProxyRequest,
    TerminateRequest,
    RemoteError,
)
from .proxy import Proxy

T = TypeVar("T")

ReturnedType: TypeAlias = Literal["copy", "proxy"]


@attrs.frozen
class MethodCaller:
    method: LiteralString

    def __call__(self, obj: Any, *args: Any, **kwargs: Any) -> Any:
        return getattr(obj, self.method)(*args, **kwargs)

    def __str__(self):
        return f"call method {self.method}"


class RPCClient:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

        self._exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(self):
        await self._exit_stack.__aenter__()
        self._exit_stack.enter_context(eliot.start_action(action_type="rpc client"))
        self._stream = await anyio.connect_tcp(self._host, self._port)
        self._receive_stream = BufferedByteReceiveStream(self._stream)
        await self._exit_stack.enter_async_context(self._stream)
        self._exit_stack.push_async_callback(self.terminate)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def call(
        self,
        fun: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        # We cancel this scope to be sure that the request always come to completion.
        # The issue is if we make a request and an external exceptions cancel waiting for the answer, then we would not
        # read the answer, and it would remain in the buffer.
        with anyio.CancelScope(shield=True):
            with eliot.start_action(action_type="call", function=str(fun)):
                with eliot.start_action(action_type="send"):
                    request = self._build_request(fun, args, kwargs, "copy")
                    pickled = pickle.dumps(request)
                    await send_with_size_prefix(self._stream, pickled)
                with eliot.start_action(action_type="receive"):
                    bytes_response = await receive_with_size_prefix(self._receive_stream)
                    response = pickle.loads(bytes_response)
                    return self._build_result(response)

    async def call_method(
        self,
        obj: Any,
        method: LiteralString,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return await self.call(
            MethodCaller(method=method),
            obj,
            *args,
            **kwargs,
        )

    async def terminate(self):
        request = TerminateRequest()
        pickled_request = pickle.dumps(request)
        await send_with_size_prefix(self._stream, pickled_request)

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
            pickled_response = await receive_with_size_prefix(self._receive_stream)
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

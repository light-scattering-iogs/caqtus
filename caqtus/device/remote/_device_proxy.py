import contextlib
import functools
from collections.abc import Callable, Coroutine, Iterator
from typing import (
    Self,
    ParamSpec,
    TypeVar,
    Generic,
    LiteralString,
    Any,
    final,
    AsyncIterator,
)

from caqtus.device import Device
from .rpc import RPCClient, Proxy, RemoteCallError

T = TypeVar("T")
P = ParamSpec("P")

DeviceType = TypeVar("DeviceType", bound=Device)


def unwrap_remote_error_decorator(fun: Callable[P, Coroutine[Any, Any, T]]):
    """Decorator that unwraps RemoteError and raises the original exception.

    It pretends that the original exception occurred on the client side.

    It is useful to help catch device specific exceptions for example timeouts, since
    then we can directly catch TimeoutError and not RemoteError.
    """

    @functools.wraps(fun)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with unwrap_remote_error_cm():
            return await fun(*args, **kwargs)

    return wrapper


@contextlib.contextmanager
def unwrap_remote_error_cm():
    try:
        yield
    except RemoteCallError as remote:
        if original := remote.__cause__:
            # Here we need to break the circle of exceptions.
            # Indeed, original.__context__ is now remote, and remote.__cause__ is
            # original.
            # If not handled, this would cause recursion issues when anything tries
            # to handle the exception down the line.
            remote.__cause__ = None
            raise original
        else:
            raise


async def unwrap_remote_error_iterator(iterator: AsyncIterator[T]) -> AsyncIterator[T]:
    stop = object()
    while True:
        with unwrap_remote_error_cm():
            next_value = await anext(iterator, default=stop)
        if next_value is stop:
            break
        yield next_value


class DeviceProxy(Generic[DeviceType]):
    """Proxy to a remote device.

    This class is used on the client side to interact with a device running on a remote
    server.
    It provides asynchronous methods to get attributes and call methods remotely
    without blocking the client.
    """

    @final
    def __init__(
        self,
        rpc_client: RPCClient,
        device_type: Callable[P, DeviceType],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self._rpc_client = rpc_client
        self._device_type = device_type
        self._args = args
        self._kwargs = kwargs
        self._device_proxy: Proxy[DeviceType]

        self._async_exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> Self:
        await self._async_exit_stack.__aenter__()
        self._device_proxy = await self._async_exit_stack.enter_async_context(
            self._rpc_client.call_proxy_result(
                self._device_type, *self._args, **self._kwargs
            )
        )
        with unwrap_remote_error_cm():
            await self._async_exit_stack.enter_async_context(
                self.async_context_manager(self._device_proxy)
            )
        return self

    @unwrap_remote_error_decorator
    async def get_attribute(self, attribute_name: LiteralString) -> Any:
        return await self._rpc_client.get_attribute(self._device_proxy, attribute_name)

    @unwrap_remote_error_decorator
    async def call_method(
        self,
        method_name: LiteralString,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return await self._rpc_client.call_method(
            self._device_proxy, method_name, *args, **kwargs
        )

    def call_method_proxy_result(
        self,
        method_name: LiteralString,
        *args: Any,
        **kwargs: Any,
    ) -> contextlib.AbstractAsyncContextManager[Proxy]:
        return self._rpc_client.call_method_proxy_result(
            self._device_proxy, method_name, *args, **kwargs
        )

    def async_context_manager(
        self, proxy: Proxy[contextlib.AbstractContextManager[T]]
    ) -> contextlib.AbstractAsyncContextManager[Proxy[T]]:
        return self._rpc_client.async_context_manager(proxy)

    def async_iterator(self, proxy: Proxy[Iterator[T]]) -> AsyncIterator[T]:
        return unwrap_remote_error_iterator(self._rpc_client.async_iterator(proxy))

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._async_exit_stack.__aexit__(exc_type, exc_value, traceback)

import contextlib
import functools
from collections.abc import Callable, Coroutine
from typing import Self, ParamSpec, TypeVar, Generic, LiteralString, Any, final

from caqtus.device import Device
from .rpc import RPCClient, Proxy, RemoteCallError

T = TypeVar("T")
P = ParamSpec("P")

DeviceType = TypeVar("DeviceType", bound=Device)


def unwrap_remote_error(fun: Callable[P, Coroutine[Any, Any, T]]):
    """Decorator that unwraps RemoteError and raises the original exception.

    It pretends that the original exception occurred on the client side.

    It is useful to help catch device specific exceptions for example timeouts, since
    then we can directly catch TimeoutError and not RemoteError.
    """

    @functools.wraps(fun)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await fun(*args, **kwargs)
        except RemoteCallError as e:
            if isinstance(e.__cause__, BaseException):
                error = e.__cause__
            else:
                error = e
            raise error from None

    return wrapper


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
        await self._async_exit_stack.enter_async_context(
            self.async_context_manager(self._device_proxy)
        )
        return self

    @unwrap_remote_error
    async def get_attribute(self, attribute_name: LiteralString) -> Any:
        return await self._rpc_client.get_attribute(self._device_proxy, attribute_name)

    @unwrap_remote_error
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

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._async_exit_stack.__aexit__(exc_type, exc_value, traceback)

import contextlib
from collections.abc import Callable, Iterator
from typing import (
    Self,
    ParamSpec,
    TypeVar,
    LiteralString,
    Any,
    final,
    AsyncIterator,
)

from ._async_converter import AsyncConverter
from .rpc import Proxy
from ..runtime import Device
from ...utils.context_managers import aclose_on_error

T = TypeVar("T")
P = ParamSpec("P")


class DeviceProxy[DeviceType: Device]:
    """Proxy to a remote device.

    This class is used on the client side to interact with a device running on a remote
    server.
    It provides asynchronous methods to get attributes and call methods remotely
    without blocking the client.
    """

    @final
    def __init__(
        self,
        async_converter: AsyncConverter,
        device_type: Callable[P, DeviceType],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        self.async_converter = async_converter
        self._device_type = device_type
        self._args = args
        self._kwargs = kwargs
        self._device_proxy: Proxy[DeviceType]

        self._async_exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> Self:
        async with aclose_on_error(self._async_exit_stack):
            self._device_proxy = await self._async_exit_stack.enter_async_context(
                self.async_converter.call_proxy_result(
                    self._device_type, *self._args, **self._kwargs
                )
            )
            await self._async_exit_stack.enter_async_context(
                self.async_context_manager(self._device_proxy)
            )
        return self

    async def get_attribute(self, attribute_name: LiteralString) -> Any:
        return await self.async_converter.get_attribute(
            self._device_proxy, attribute_name
        )

    async def call_method(
        self,
        method_name: LiteralString,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return await self.async_converter.call_method(
            self._device_proxy, method_name, *args, **kwargs
        )

    def call_method_proxy_result(
        self,
        method_name: LiteralString,
        *args: Any,
        **kwargs: Any,
    ) -> contextlib.AbstractAsyncContextManager[Proxy]:
        return self.async_converter.call_method_proxy_result(
            self._device_proxy, method_name, *args, **kwargs
        )

    def async_context_manager(
        self, proxy: Proxy[contextlib.AbstractContextManager[T]]
    ) -> contextlib.AbstractAsyncContextManager[Proxy[T]]:
        return self.async_converter.async_context_manager(proxy)

    def async_iterator(self, proxy: Proxy[Iterator[T]]) -> AsyncIterator[T]:
        return self.async_converter.async_iterator(proxy)

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._async_exit_stack.__aexit__(exc_type, exc_value, traceback)

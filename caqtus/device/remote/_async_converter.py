import abc
import contextlib
from collections.abc import Callable, Iterator, AsyncIterator
from typing import Protocol, LiteralString

from caqtus.device.remote.rpc import Proxy


class AsyncConverter(Protocol):
    """Transform synchronous calls into asynchronous ones.

    To support subprocess calls, all function arguments must be either pickleable or a
    proxy to a remote object.
    """

    @abc.abstractmethod
    async def call[
        T,
    ](self, fun: Callable[..., T], *args, **kwargs) -> T:
        """Call a function asynchronously.

        Args:
            fun: The function to call.
            args: The positional arguments to pass to the function.
            kwargs: The keyword arguments to pass to the function.

        Returns:
            A copy of the return value of the function.

        Warning:
            To support subprocess calls, all arguments must be
            and the return value must be
            pickleable.
        """

        raise NotImplementedError

    @abc.abstractmethod
    async def call_method(
        self,
        obj,
        method: LiteralString,
        *args,
        **kwargs,
    ):
        """Call an object's method asynchronously.

        Args:
            obj: The object on which to call the method.

                It must be either pickleable or a proxy to a remote object.

            method: The name of the method to call.
            args: The positional arguments to pass to the method.

                They must be pickleable.

            kwargs: The keyword arguments to pass to the method.

                They must be pickleable.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def call_method_proxy_result(
        self,
        obj,
        method: LiteralString,
        *args,
        **kwargs,
    ) -> contextlib.AbstractAsyncContextManager[Proxy]:
        """Call an object's method and return a proxy to the result.

        Args:
            obj: The object on which to call the method.

                Must be pickleable or a proxy to a remote object.

            method: The name of the method to call.
            args: The positional arguments to pass to the method.

                Must be pickleable.

            kwargs: The keyword arguments to pass to the method.

                Must be pickleable.

        Returns:
            An async context manager that yields a proxy to the result of the method
            call.
        """

        raise NotImplementedError

    @abc.abstractmethod
    async def get_attribute(self, obj, attribute: LiteralString):
        """Get an object's attribute asynchronously.

        Args:
            obj: The object from which to get the attribute.

                Must be pickleable or a proxy to a remote object.

            attribute: The name of the attribute to get.

        Returns:
            A copy of the attribute's value.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def call_proxy_result[
        T
    ](
        self, fun: Callable[..., T], *args, **kwargs
    ) -> contextlib.AbstractAsyncContextManager[Proxy[T]]:
        """Call a function and return a proxy to the result."""

        raise NotImplementedError

    @abc.abstractmethod
    def async_context_manager[
        T
    ](
        self, cm_proxy: Proxy[contextlib.AbstractContextManager[T]]
    ) -> contextlib.AbstractAsyncContextManager[Proxy[T], None]:
        """Wrap an async context manager proxy.

        Returns:
            An async context manager that yields a proxy to the result of context
            manager's __enter__ method.
        """

        raise NotImplementedError

    @abc.abstractmethod
    def async_iterator[T](self, proxy: Proxy[Iterator[T]]) -> AsyncIterator[T]:
        """Iterate over a remote iterator asynchronously."""

        raise NotImplementedError

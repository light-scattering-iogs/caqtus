import functools
import logging
import os
import pickle
import warnings
from collections.abc import Callable
from enum import Enum, auto
from typing import Never, Any, TypeVar, Self

import anyio
import anyio.to_thread
import attrs

from ._configuration import (
    RPCConfiguration,
)
from ._prefix_size import receive_with_size_prefix, send_with_size_prefix
from .proxy import Proxy
from .server import RemoteError, InvalidProxyError

logger = logging.getLogger(__name__)


@attrs.define
class ObjectReference:
    obj: object
    number_proxies: int


class ReturnValue(Enum):
    SERIALIZED = auto()
    PROXY = auto()


@attrs.define
class CallRequest:
    function: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    return_value: ReturnValue


@attrs.define
class DeleteProxyRequest:
    proxy: Proxy


@attrs.define
class CallResponseFailure:
    error: Exception


@attrs.define
class CallResponseSuccess:
    result: Any


CallResponse = CallResponseFailure | CallResponseSuccess

T = TypeVar("T")


class RPCServer:
    def __init__(self, port: int):
        self._port = port
        self._objects: dict[int, ObjectReference] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._objects:
            warnings.warn(
                f"Not all objects were properly deleted: {self._objects}.\n"
                f"If you acquired any proxies, make sure to close them."
            )
            self._objects.clear()

    async def run_async(self) -> Never:
        listener = await anyio.create_tcp_listener(local_port=self._port)
        await listener.serve(self.handle)

    async def handle(self, client):
        async with client:
            request_bytes = await receive_with_size_prefix(client)
            request = pickle.loads(request_bytes)
            if isinstance(request, CallRequest):
                await self.handle_call_request(client, request)
            elif isinstance(request, DeleteProxyRequest):
                self.handle_delete_proxy_request(request)

    async def handle_call_request(self, client, request: CallRequest) -> None:
        try:
            args = [self.resolve(arg) for arg in request.args]
            kwargs = {key: self.resolve(value) for key, value in request.kwargs.items()}
            value = await anyio.to_thread.run_sync(
                functools.partial(request.function, *args, **kwargs)
            )

            if request.return_value == ReturnValue.SERIALIZED:
                result = value
            elif request.return_value == ReturnValue.PROXY:
                result = self.create_proxy(value)
            else:
                assert False, f"Unknown return value: {request.return_value}"
            result = CallResponseSuccess(result=result)
        except StopIteration as e:
            # Don't log this exception, as it can occur during normal operation if we're
            # calling __next__ on an iterator.
            result = self._construct_error_response(request.function, e)
        except Exception as e:
            logger.exception(
                f"Error during call with request {request!r}", exc_info=True
            )
            result = self._construct_error_response(request.function, e)

        pickled_result = pickle.dumps(result)
        await send_with_size_prefix(client, pickled_result)

    def handle_delete_proxy_request(self, request: DeleteProxyRequest) -> None:
        proxy = request.proxy
        if proxy._pid != os.getpid():
            raise RuntimeError(
                "Proxy cannot be deleted in a different process than the one it was "
                "created in"
            )
        self._objects[proxy._obj_id].number_proxies -= 1
        if self._objects[proxy._obj_id].number_proxies <= 0:
            del self._objects[proxy._obj_id]

    @staticmethod
    def _construct_error_response(fun, e: Exception) -> CallResponseFailure:
        error = RemoteError(f"Error during call to {fun}")
        error.__cause__ = e
        return CallResponseFailure(error=error)

    def create_proxy(self, obj: T) -> Proxy[T]:
        obj_id = id(obj)
        if obj_id not in self._objects:
            self._objects[obj_id] = ObjectReference(obj=obj, number_proxies=0)
        proxy = Proxy(os.getpid(), obj_id)
        self._objects[obj_id].number_proxies += 1
        return proxy

    def get_referent(self, proxy: Proxy[T]) -> T:
        if proxy._pid != os.getpid():
            raise RuntimeError(
                "Proxy cannot be resolved in a different process than the one it was "
                "created in"
            )
        try:
            return self._objects[proxy._obj_id].obj
        except KeyError as e:
            raise InvalidProxyError(
                f"{proxy} is referring to an object that does not exist on the "
                f"server"
            ) from e

    def resolve(self, obj: Proxy[T] | T) -> T:
        if isinstance(obj, Proxy):
            return self.get_referent(obj)
        else:
            return obj

    def run(self) -> Never:
        anyio.run(self.run_async)


class Server:
    def __init__(self, config: RPCConfiguration) -> None:
        self._server = RPCServer(config.port)

    def wait_for_termination(self) -> None:
        self._server.run()

    def __enter__(self) -> Self:
        self._server.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._server.__exit__(exc_type, exc_value, traceback)
        logger.info("Server stopped")

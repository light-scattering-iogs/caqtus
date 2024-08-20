import contextlib
import functools
import itertools
import logging
import os
import pickle
import warnings
from collections.abc import Callable
from enum import Enum, auto
from typing import Never, Any, TypeVar, Self, ParamSpec

import anyio
import anyio.abc
import anyio.to_thread
import attrs
import tblib.pickling_support
from anyio.streams.buffered import BufferedByteReceiveStream

from ._configuration import RPCConfiguration
from ._prefix_size import receive_with_size_prefix, send_with_size_prefix
from .._proxy import Proxy

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
    id_: int
    function: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    return_value: ReturnValue


@attrs.define
class DeleteProxyRequest:
    id_: int
    proxy: Proxy


Request = CallRequest | DeleteProxyRequest


@attrs.define
class CallResponseFailure:
    id_: int
    error: Exception


@attrs.define
class CallResponseSuccess:
    id_: int
    result: Any


class TerminateRequest:
    pass


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
        async with contextlib.aclosing(listener):
            await listener.serve(self.handle)

    async def handle(self, client: anyio.abc.ByteStream) -> None:
        async with client:
            receive_stream = BufferedByteReceiveStream(client)
            for _ in itertools.count():
                request_bytes = await receive_with_size_prefix(receive_stream)
                request = pickle.loads(request_bytes)
                if isinstance(request, CallRequest):
                    await self.handle_call_request(client, request)
                elif isinstance(request, DeleteProxyRequest):
                    self.handle_delete_proxy_request(request)
                elif isinstance(request, TerminateRequest):
                    break
                else:
                    raise ValueError(f"Unknown request type: {request}")

    async def handle_call_request(self, client, request: CallRequest) -> None:
        try:
            args = [self.resolve(arg) for arg in request.args]
            kwargs = {key: self.resolve(value) for key, value in request.kwargs.items()}
            # We can't have the function raise StopIteration since the coroutine will
            # then raise this exception which is invalid.
            # To prevent this, we replace StopIteration with our own exception.
            fun = _transform_stop_iteration(request.function)
            value = await anyio.to_thread.run_sync(
                functools.partial(fun, *args, **kwargs)
            )

            if request.return_value == ReturnValue.SERIALIZED:
                result = value
            elif request.return_value == ReturnValue.PROXY:
                result = self.create_proxy(value)
            else:
                assert False, f"Unknown return value: {request.return_value}"
        except _StopIteration:
            # Don't log this exception, as it can occur during normal operation if we're
            # calling __next__ on an iterator.
            await self.send_failure_response(client, request, StopIteration())
        except Exception as e:
            logger.exception(f"Error during request call {request!r}")
            await self.send_failure_response(client, request, e)
        else:
            await self.send_success_response(client, request, result)

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
    async def send_failure_response(
        client: anyio.abc.ByteStream, request: CallRequest, e: Exception
    ) -> None:
        try:
            raise RemoteCallError(f"Error during call to {request.function}") from e
        except RemoteCallError as error:
            response = CallResponseFailure(error=error, id_=request.id_)
        pickled_response = pickle.dumps(response)
        await send_with_size_prefix(client, pickled_response)

    @staticmethod
    async def send_success_response(
        client: anyio.abc.ByteStream, request: CallRequest, result: Any
    ) -> None:
        response = CallResponseSuccess(result=result, id_=request.id_)
        pickled_response = pickle.dumps(response)
        await send_with_size_prefix(client, pickled_response)

    def create_proxy(self, obj: T) -> Proxy[T]:
        obj_id = id(obj)
        if obj_id not in self._objects:
            self._objects[obj_id] = ObjectReference(obj=obj, number_proxies=0)
        proxy = Proxy(os.getpid(), obj_id)
        self._objects[obj_id].number_proxies += 1
        return proxy

    def get_referent(self, proxy: Proxy[T]) -> T:
        if proxy._pid != os.getpid():
            raise InvalidProxyError(
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
        anyio.run(self.run_async, backend="trio")


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


class RemoteError(Exception):
    """Base class for errors that occur on the server side."""

    pass


class RemoteCallError(RemoteError):
    """Error that occurs when calling a remote function."""

    pass


class InvalidProxyError(RemoteError):
    pass


tblib.pickling_support.install(RemoteError, RemoteCallError, InvalidProxyError)


P = ParamSpec("P")


def _transform_stop_iteration(fun: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(fun)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return fun(*args, **kwargs)
        except StopIteration:
            raise _StopIteration() from None

    return wrapper


class _StopIteration(BaseException):
    pass

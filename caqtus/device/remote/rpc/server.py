import concurrent.futures
import contextlib
import logging
import os
import pickle
import warnings
from typing import TypeVar, Self

import attrs
import grpc
import tblib.pickling_support

from . import rpc_pb2
from . import rpc_pb2_grpc
from .proxy import Proxy

tblib.pickling_support.install()

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Server:
    def __init__(self, address: str, credentials: grpc.ServerCredentials) -> None:
        self._server = grpc.server(concurrent.futures.ThreadPoolExecutor())
        self._servicer = RemoteCallServicer()
        rpc_pb2_grpc.add_RemoteCallServicer_to_server(self._servicer, self._server)
        self._server.add_secure_port(address=address, server_credentials=credentials)
        self._exit_stack = contextlib.ExitStack()

    def __enter__(self) -> Self:
        self._exit_stack.__enter__()
        self._server.start()
        self._exit_stack.callback(self._server.stop, grace=5)
        self._exit_stack.enter_context(self._servicer)
        logger.info("Server started")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._exit_stack.__exit__(exc_type, exc_value, traceback)
        logger.info("Server stopped")


@attrs.define
class ObjectReference:
    obj: object
    number_proxies: int


# noinspection PyProtectedMember
class RemoteCallServicer(rpc_pb2_grpc.RemoteCallServicer):
    def __init__(self) -> None:
        self._objects: dict[int, ObjectReference] = {}

    def Call(self, request: rpc_pb2.CallRequest, context) -> rpc_pb2.CallResponse:
        try:
            fun = pickle.loads(request.function)
        except pickle.UnpicklingError as e:
            error = RemoteCallError("Error during call")
            error.__cause__ = e
            return rpc_pb2.CallResponse(failure=pickle.dumps(error))
        try:
            args = [self.resolve(pickle.loads(arg)) for arg in request.args]
            kwargs = {
                key: self.resolve(pickle.loads(value))
                for key, value in request.kwargs.items()
            }
            logger.info(f"Calling {fun} with {args} and {kwargs}")
            value = fun(*args, **kwargs)

            if request.return_value == rpc_pb2.ReturnValue.SERIALIZED:
                result = value
            elif request.return_value == rpc_pb2.ReturnValue.PROXY:
                result = self.create_proxy(value)
            else:
                assert False, f"Unknown return value: {request.return_value}"
            return rpc_pb2.CallResponse(success=pickle.dumps(result))
        except Exception as e:
            logger.exception(
                f"Error during call with request {request!r}", exc_info=True
            )
            return self._construct_error_response(fun, e)

    @staticmethod
    def _construct_error_response(fun, e: Exception) -> rpc_pb2.CallResponse:
        error = RemoteError(f"Error during call to {fun}")
        error.__cause__ = e
        try:
            pickled = pickle.dumps(error)
        except pickle.PicklingError:
            # It can happen that the cause error cannot be pickled.
            # In this case we convert it to a string.
            error.__cause__ = None
            error = RemoteCallError(f"Error during call to {fun}: {e}")
            pickled = pickle.dumps(error)
        return rpc_pb2.CallResponse(failure=pickled)

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

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._objects:
            warnings.warn(
                f"Not all objects were properly deleted: {self._objects}.\n"
                f"If you acquired any proxies, make sure to close them."
            )
            self._objects.clear()

    def DeleteReferent(
        self, request: rpc_pb2.DeleteReferentRequest, context
    ) -> rpc_pb2.DeleteReferentResponse:
        proxy = pickle.loads(request.proxy)
        assert isinstance(proxy, Proxy)

        if proxy._pid != os.getpid():
            raise RuntimeError(
                "Proxy cannot be deleted in a different process than the one it was "
                "created in"
            )
        self._objects[proxy._obj_id].number_proxies -= 1
        if self._objects[proxy._obj_id].number_proxies <= 0:
            del self._objects[proxy._obj_id]
        return rpc_pb2.DeleteReferentResponse(success=True)


class RemoteError(Exception):
    pass


class InvalidProxyError(RemoteError):
    pass


class RemoteCallError(RemoteError):
    pass

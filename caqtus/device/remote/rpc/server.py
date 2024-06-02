import concurrent.futures
import contextlib
import logging
import os
import pickle
import warnings
from typing import TypeVar, Self

import grpc
import tblib.pickling_support

from . import rpc_pb2
from . import rpc_pb2_grpc
from .proxy import Proxy

tblib.pickling_support.install()

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Server:
    def __init__(self) -> None:
        self._server = grpc.server(concurrent.futures.ThreadPoolExecutor())
        self._servicer = RemoteCallServicer()
        rpc_pb2_grpc.add_RemoteCallServicer_to_server(self._servicer, self._server)
        self._server.add_insecure_port("[::]:50051")
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


# noinspection PyProtectedMember
class RemoteCallServicer(rpc_pb2_grpc.RemoteCallServicer):
    def __init__(self) -> None:
        self._objects: dict[int, object] = {}

    def Call(self, request: rpc_pb2.CallRequest, context) -> rpc_pb2.CallResponse:
        fun = pickle.loads(request.function)
        args = [self.resolve(pickle.loads(arg)) for arg in request.args]
        kwargs = {
            key: self.resolve(pickle.loads(value))
            for key, value in request.kwargs.items()
        }
        logger.info(f"Calling {fun} with {args} and {kwargs}")
        try:
            value = fun(*args, **kwargs)
        except Exception as e:
            logger.error(e)
            remote_error = RemoteCallError(f"An error occurred while calling {fun}")
            remote_error.__cause__ = e
            return rpc_pb2.CallResponse(failure=pickle.dumps(remote_error))
        else:
            if request.return_value == rpc_pb2.ReturnValue.SERIALIZED:
                result = value
            elif request.return_value == rpc_pb2.ReturnValue.PROXY:
                result = self.create_proxy(value)
            else:
                assert False, f"Unknown return value: {request.return_value}"
            return rpc_pb2.CallResponse(success=pickle.dumps(result))

    def create_proxy(self, obj: T) -> Proxy[T]:
        obj_id = id(obj)
        self._objects[obj_id] = obj
        return Proxy(os.getpid(), obj_id)

    def get_referent(self, proxy: Proxy[T]) -> T:
        if proxy._pid != os.getpid():
            raise RuntimeError(
                "Proxy cannot be resolved in a different process than the one it was "
                "created in"
            )
        return self._objects[proxy._obj_id]

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
        del self._objects[proxy._obj_id]
        return rpc_pb2.DeleteReferentResponse(success=True)


class RemoteError(Exception):
    pass


class RemoteCallError(RemoteError):
    pass

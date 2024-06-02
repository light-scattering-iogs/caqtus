import concurrent.futures
import logging
import os
import pickle
from typing import TypeVar, Self

import grpc

import rpc_pb2
import rpc_pb2_grpc
from .proxy import Proxy

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Server:
    def __init__(self) -> None:
        self._server = grpc.server(concurrent.futures.ThreadPoolExecutor())
        rpc_pb2_grpc.add_RemoteCallServicer_to_server(
            RemoteCallServicer(), self._server
        )
        self._server.add_insecure_port("[::]:50051")

    def __enter__(self) -> Self:
        self._server.start()
        logger.info("Server started")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._server.stop()
        logger.info("Server stopped")


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


class RemoteError(Exception):
    pass


class RemoteCallError(RemoteError):
    pass

import threading
from functools import wraps
from typing import Concatenate, Callable, Protocol, TypeVar, ParamSpec

_P = ParamSpec("_P")
_T = TypeVar("_T")


class Lockable(Protocol):
    lock: threading.Lock


def with_lock(
    method: Callable[Concatenate[Lockable, _P], _T]
) -> Callable[Concatenate[Lockable, _P], _T]:
    @wraps(method)
    def wrapper(self: Lockable, *args: _P.args, **kwargs: _P.kwargs):
        with self.lock:
            return method(self, *args, **kwargs)

    return wrapper

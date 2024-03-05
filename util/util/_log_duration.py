import logging
import time
from functools import wraps
from typing import ParamSpec, TypeVar, Callable

_P = ParamSpec("_P")
_T = TypeVar("_T")


def log_duration(
    logger: logging.Logger,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        @wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            t0 = time.time()
            result = func(*args, **kwargs)
            t1 = time.time()
            logger.debug(f"{func.__name__} took {(t1 - t0)*1e3:.2f} ms.")
            return result

        return wrapper

    return decorator

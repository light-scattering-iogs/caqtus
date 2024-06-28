import contextlib
import functools
import logging


from typing import Callable, TypeVar, ParamSpec


_P = ParamSpec("_P")
_T = TypeVar("_T")


def log_cm(logger: logging.Logger, level: int = logging.DEBUG):
    """Decorator to log the start and end of a context manager."""

    def decorator(
        func: Callable[_P, contextlib.AbstractContextManager[_T]]
    ) -> Callable[_P, contextlib.AbstractContextManager[_T]]:
        @functools.wraps(func)
        @contextlib.contextmanager
        def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            logger.log(level, f"Entering context manager %s.", func.__name__)
            with func(*args, **kwargs) as cm:
                yield cm
            logger.log(level, f"Exiting context manager %s.", func.__name__)

        return wrapper

    return decorator


def log_async_cm(logger: logging.Logger, level: int = logging.DEBUG):
    """Decorator to log the start and end of an asynchronous context manager."""

    def decorator(
        func: Callable[_P, contextlib.AbstractAsyncContextManager[_T]]
    ) -> Callable[_P, contextlib.AbstractAsyncContextManager[_T]]:
        @functools.wraps(func)
        @contextlib.asynccontextmanager
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            logger.log(level, f"Entering context manager %s.", func.__name__)
            async with func(*args, **kwargs) as cm:
                yield cm
            logger.log(level, f"Exiting context manager %s.", func.__name__)

        return wrapper

    return decorator

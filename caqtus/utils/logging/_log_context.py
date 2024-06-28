import contextlib
import functools
import logging

from typing import Callable, TypeVar, ParamSpec, Optional

_P = ParamSpec("_P")
_T = TypeVar("_T")


def log_cm_decorator(logger: logging.Logger, level: int = logging.DEBUG):
    """Decorator to log the start and end of a context manager."""

    def decorator(
        func: Callable[_P, contextlib.AbstractContextManager[_T]]
    ) -> Callable[_P, contextlib.AbstractContextManager[_T]]:
        @functools.wraps(func)
        @contextlib.contextmanager
        def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            logger.log(level, f"Enter cm: %s.", func.__name__)
            with func(*args, **kwargs) as cm:
                yield cm
            logger.log(level, f"Exit  cm: %s.", func.__name__)

        return wrapper

    return decorator


def log_async_cm_decorator(logger: logging.Logger, level: int = logging.DEBUG):
    """Decorator to log the start and end of an asynchronous context manager."""

    def decorator(
        func: Callable[_P, contextlib.AbstractAsyncContextManager[_T]]
    ) -> Callable[_P, contextlib.AbstractAsyncContextManager[_T]]:
        @functools.wraps(func)
        @contextlib.asynccontextmanager
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs):
            logger.log(level, f"Enter cm: %s.", func.__name__)
            async with func(*args, **kwargs) as cm:
                yield cm
            logger.log(level, f"Exit  cm: %s.", func.__name__)

        return wrapper

    return decorator


@contextlib.asynccontextmanager
async def log_async_cm(
    cm: contextlib.AbstractAsyncContextManager[_T],
    logger: logging.Logger,
    name: Optional[str] = None,
    level: int = logging.DEBUG,
):
    """Transformer to log the start and end of an asynchronous context manager."""

    to_print = cm if name is None else name
    logger.log(level, "Enter cm: %s.", to_print)
    try:
        async with cm as value:
            yield value
    finally:
        logger.log(level, f"Exit  cm: %s.", to_print)

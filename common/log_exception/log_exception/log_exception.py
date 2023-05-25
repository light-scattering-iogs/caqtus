import logging
from functools import wraps
from typing import ParamSpec, TypeVar, Callable

_P = ParamSpec("_P")
_T = TypeVar("_T")


def log_exception(
    logger: logging.Logger,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator to log exceptions raised by a function.

    Args:
        logger: The logger to use to record the exception.
    """

    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        @wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.exception(
                    f"An error occurred when executing {func.__name__}.",
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator

import functools
import logging

from typing import Callable, TypeVar, ParamSpec

_P = ParamSpec("_P")
_T = TypeVar("_T")


def log_call(
    logger: logging.Logger, log_args=True, log_result=True, level: int = logging.DEBUG
):
    """Decorator to log calls to a function.

    Args:
        logger: The logger to use to record the call.
        log_args: Indicate if the arguments passed to the function needs to be logged.
        log_result: Indicate if the result of the function needs to be logged.
        level: The logging level to use.
    """

    def decorator(func: Callable[_P, _T]) -> Callable[_P, _T]:
        @functools.wraps(func)
        def wrapper(
            *args: _P.args,
            **kwargs: _P.kwargs,
        ) -> _T:
            if log_args:
                logger.log(
                    level,
                    f"Calling %s with args %r and kwargs %r.",
                    func.__name__,
                    args,
                    kwargs,
                )
            else:
                logger.log(level, f"Calling %s.", func.__name__)
            result = func(*args, **kwargs)
            if log_result:
                logger.log(
                    level, f"Finished calling %s, returning %s.", func.__name__, result
                )
            else:
                logger.log(level, f"Finished calling %s.", func.__name__)
            return result

        return wrapper

    return decorator

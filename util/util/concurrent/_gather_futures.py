import concurrent.futures
from collections.abc import Iterable, Callable
from concurrent.futures import Future
from typing import TypeVar, ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


def gather_futures(futures: Iterable[Future[T]]) -> list[T]:
    """Gather the result all futures into a list.

    Args:
        futures: An iterable of futures.

    Returns:
        A list of the results of the futures.

    Raises:
        An ExceptionGroup containing all exceptions raised by the futures.
    """

    results = []
    exceptions = []

    for future in futures:
        if exception := future.exception():
            exceptions.append(exception)
        else:
            results.append(future.result())

    if exceptions:
        if not all(isinstance(exception, Exception) for exception in exceptions):
            raise BaseExceptionGroup(
                f"Unhandled exceptions ({len(exceptions)}) in futures", exceptions
            )
        else:
            raise ExceptionGroup(
                f"Unhandled exceptions ({len(exceptions)}) in futures", exceptions  # type: ignore
            )

    return results


class TaskGroup:
    def __init__(self, executor: concurrent.futures.Executor):
        self._executor = executor
        self._futures: list[Future] = []

    def __enter__(self):
        if self._futures:
            raise RuntimeError("TaskGroup is already entered")
        self._futures = []
        return self

    def create_task(
        self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> concurrent.futures.Future[T]:
        future = self._executor.submit(func, *args, **kwargs)
        self._futures.append(future)
        return future

    def __exit__(self, exc_type, exc_val, exc_tb):
        gather_futures(self._futures)
        self._futures = []

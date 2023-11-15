import concurrent.futures
from collections.abc import Iterable, Callable
from concurrent.futures import Future
from typing import TypeVar, ParamSpec, Optional

T = TypeVar("T")
P = ParamSpec("P")


def _gather_futures(futures: Iterable[Future[T]], name: Optional[str]) -> list[T]:
    """Gather the result all futures into a list.

    Args:
        futures: An iterable of futures.
        name: The name of the task group, used for error messages.

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
        if name is None:
            msg = f"Unhandled exceptions ({len(exceptions)}) in task group"
        else:
            msg = f"Unhandled exceptions ({len(exceptions)}) in task group {name}"
        if not all(isinstance(exception, Exception) for exception in exceptions):
            raise BaseExceptionGroup(msg, exceptions)
        else:
            raise ExceptionGroup(msg, exceptions)  # type: ignore

    return results


class TaskGroup:
    def __init__(
        self, executor: concurrent.futures.Executor, /, name: Optional[str] = None
    ):
        self._executor = executor
        self._name = name
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
        _gather_futures(self._futures, name=self._name)
        self._futures = []

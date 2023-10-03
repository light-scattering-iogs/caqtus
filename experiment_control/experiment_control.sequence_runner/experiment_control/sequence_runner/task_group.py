from concurrent.futures import Executor, Future
from contextlib import AbstractContextManager
from typing import Callable, TypeVar, ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


class TaskGroup(AbstractContextManager):
    def __init__(self, executor: Executor):
        self._executor = executor
        self._futures: list[Future] = []
        self._entered = False

    def __enter__(self):
        self._futures = []
        self._entered = True
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._entered = False
        exceptions = []
        for future in self._futures:
            exception = future.exception()
            if exception is not None:
                exceptions.append(exception)
        if exceptions:
            raise ExceptionGroup("Unhandled exception(s) occurred", exceptions)

    def add_task(
        self, task: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> Future[T]:
        if not self._entered:
            raise RuntimeError("Cannot add tasks to a TaskGroup that is not entered.")
        future = self._executor.submit(task, *args, **kwargs)
        self._futures.append(future)
        return future

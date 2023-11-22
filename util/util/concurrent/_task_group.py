import concurrent.futures
from collections.abc import Iterable, Callable
from concurrent.futures import Future
from typing import TypeVar, ParamSpec, Optional, Self

T = TypeVar("T")
P = ParamSpec("P")


class TaskGroup:
    """A context manager that group tasks and waits for them to finish.

    This is a wrapper around a concurrent.futures.Executor that allows you to run tasks in parallel and then wait for
    them to finish. It is similar to asyncio.TaskGroup, but it uses a concurrent.futures executor instead of asyncio
    tasks. Once entered, tasks can be created using the create_task() method. The tasks will be executed in the
    background using the executor passed to the constructor. When the context manager is exited, all tasks will be
    waited for and any exceptions raised by the tasks will be raised in the main thread.

    Note that unlike asyncio.TaskGroup, no scheduled task will ever be cancelled, even if an exception occurs in one of
    the tasks. This is because there is no general mechanism to cancel an arbitrary task.
    """

    def __init__(
        self, executor: concurrent.futures.Executor, /, name: Optional[str] = None
    ) -> None:
        """Initialize a new TaskGroup.

        Args:
            executor: The executor to use for running the tasks. The executor must be active before creating a task.
            name: The name of the task group, used for error messages.
        """

        self._executor = executor
        self._name = name
        self._futures: list[Future] = []

    def __enter__(self) -> Self:
        """Enter the task group.

        The task group can only be entered once. If it is entered a second time, a RuntimeError will be raised. Entering
        the task group will not initialize the executor, this must be done separately.
        """

        if self._futures:
            raise RuntimeError("TaskGroup is already entered")
        self._futures = []
        return self

    def create_task(
        self, func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> concurrent.futures.Future[T]:
        """Create a new task.

        The task will be executed in the background using the executor passed to the constructor.

        Args:
            func: The function to execute.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            A future representing the potential result of the task. Even if the future is discarded, the task will still
            be executed in the background and any exceptions raised by the task will be raised when the task group is
            exited.
        """

        future = self._executor.submit(func, *args, **kwargs)
        self._futures.append(future)
        return future

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Wait for all tasks to finish.

        If any of the tasks raised an exception, an ExceptionGroup containing all exceptions raised by the tasks will be
        raised. Exiting the task group will not shut down the executor, this must be done separately.
        """

        self._gather_futures(self._futures)
        self._futures = []

    def get_running_tasks(self) -> list[Future]:
        """Get all the tasks that are still running."""

        return [future for future in self._futures if not future.done()]

    def _gather_futures(self, futures: Iterable[Future[T]]) -> list[T]:
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
            if self._name is None:
                msg = f"Unhandled exceptions in task group"
            else:
                msg = f"Unhandled exceptions in task group {self._name}"
            if not all(isinstance(exception, Exception) for exception in exceptions):
                raise BaseExceptionGroup(msg, exceptions)
            else:
                raise ExceptionGroup(msg, exceptions)  # type: ignore

        return results

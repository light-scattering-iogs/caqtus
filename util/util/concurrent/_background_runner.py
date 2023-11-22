import asyncio
import concurrent.futures
import contextlib
import threading
from typing import Callable, TypeVar, ParamSpec, SupportsFloat

P = ParamSpec("P")
T = TypeVar("T")


class BackgroundRunner:
    """Runs a task periodically in a separate thread."""

    def __init__(
        self,
        func: Callable[P, T],
        interval: SupportsFloat,
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._interval = float(interval)
        self._exit_stack = contextlib.ExitStack()

        self._lock = threading.Lock()

        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def __enter__(self):
        self._exit_stack.__enter__()
        self._exit_stack.enter_context(self._thread_pool)
        self._future = self._thread_pool.submit(asyncio.run, self._run())
        self._exit_stack.callback(self.stop)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._exit_stack.__exit__(exc_type, exc_val, exc_tb)

    def is_running(self) -> bool:
        return self._asyncio_loop.is_running()

    def check_error(self) -> None:
        """Can be used to check if an error occurred in the background thread.

        It will raise a BackgroundException wrapping the original exception, should one have occurred. If no exception
        occurred, this method will return normally.
        """

        if self._future.done():
            try:
                self._future.result()
            except Exception as e:
                raise BackgroundException(
                    f"An error occurred while running background task {self._func}"
                ) from e

    def stop(self) -> None:
        with self._lock:
            if self.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._cancel(), self._asyncio_loop
                ).result()
        try:
            self._future.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            raise BackgroundException(
                f"An error occurred while running background task {self._func}"
            ) from e

    async def _run(self):
        self._task = asyncio.create_task(self._loop())
        self._asyncio_loop = asyncio.get_running_loop()
        await self._task

    async def _cancel(self):
        self._task.cancel()

    async def _loop(self):
        while True:
            with self._lock:
                self._func(*self._args, **self._kwargs)
            await asyncio.sleep(self._interval)


class BackgroundException(Exception):
    pass

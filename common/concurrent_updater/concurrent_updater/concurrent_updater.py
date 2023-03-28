import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ConcurrentUpdater:
    """Calls a function periodically in a separate daemon thread

    Since this class uses a daemon thread, it is not necessary to call stop() to stop the thread. However, it is still a
    good idea to call stop() to ensure that the thread is stopped before the program exits. Errors occurring in the
    target function are logged and raised in the daemon thread.

    Args:
        target: The function to call
        watch_interval: The interval between calls, in seconds. This is the time between the end of a call and the start
            of the next one. It does not include the time the function takes to execute.
        name: The name of the thread. If not provided, the name of the target function is used.
        *args: Positional arguments to pass to the target function.
        **kwargs: Keyword arguments to pass to the target function.
    """

    def __init__(self, target: Callable, watch_interval: float = 1, name: Optional[str] = None, *args, **kwargs):
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._watch_interval = watch_interval
        if name is None:
            name = target.__name__
        self._name = name
        self._thread = threading.Thread(target=self._update, name=self._name, daemon=True)
        self._must_stop = threading.Event()
        self._lock = threading.Lock()

    def __del__(self):
        self.stop()

    def start(self):
        """Starts the to execute the target function periodically"""

        with self._lock:
            self._must_stop.clear()
            self._thread.start()

    def _update(self):
        while not self._must_stop.is_set():
            try:
                self._target(*self._args, **self._kwargs)
            except Exception:
                logger.exception(f"Error in thread {self._name}", exc_info=True)
                raise
            self._must_stop.wait(self._watch_interval)

    def stop(self):
        """Stops the daemon thread as soon as possible

        If the thread is currently executing the target function, it will finish before stopping.
        """

        with self._lock:
            self._must_stop.set()
            if self._thread.is_alive():
                self._thread.join()

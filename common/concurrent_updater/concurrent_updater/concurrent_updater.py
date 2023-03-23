import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ConcurrentUpdater:
    """Calls a function periodically in a separate thread"""

    def __init__(self, target: Callable, watch_interval: float = 1):
        self._target = target
        self._watch_interval = watch_interval
        self._thread = threading.Thread(target=self._watch)
        self._must_stop = threading.Event()
        self._lock = threading.Lock()

    def __del__(self):
        self.stop()

    def start(self):
        with self._lock:
            self._must_stop.clear()
            self._thread.start()

    def _watch(self):
        while not self._must_stop.is_set():
            self._target()
            self._must_stop.wait(self._watch_interval)

    def stop(self):
        with self._lock:
            self._must_stop.set()
            if self._thread.is_alive():
                self._thread.join()

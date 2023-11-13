import contextlib
import datetime
import logging
from typing import Self


class DurationTimer(contextlib.AbstractContextManager):
    """A timer that measures the duration of a context."""

    def __init__(self):
        self._start_time = None
        self._end_time = None

    def __enter__(self) -> Self:
        self._start_time = datetime.datetime.now(datetime.timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._end_time = datetime.datetime.now(datetime.timezone.utc)

    @property
    def duration(self) -> datetime.timedelta:
        return self.end_time - self.start_time

    @property
    def duration_in_s(self) -> float:
        return self.duration.total_seconds()

    @property
    def duration_in_ms(self) -> float:
        return self.duration_in_s * 1000

    @property
    def start_time(self) -> datetime.datetime:
        if self._start_time is None:
            raise RuntimeError("Timer has not been started yet.")
        else:
            return self._start_time

    @property
    def end_time(self) -> datetime.datetime:
        if self._end_time is None:
            raise RuntimeError("Timer has not been stopped yet.")
        else:
            return self._end_time


class DurationTimerLog(DurationTimer):
    def __init__(
        self, logger: logging.Logger, message: str, display_start: bool = False
    ):
        super().__init__()
        self._logger = logger
        self._message = message
        self._display_start = display_start

    def __enter__(self) -> Self:
        super().__enter__()
        if self._display_start:
            self._logger.info(f"Started:\t {self._message}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)
        if exc_type is None:
            self._logger.info(
                f"Finished:\t {self._message} in {self.duration_in_ms} ms"
            )

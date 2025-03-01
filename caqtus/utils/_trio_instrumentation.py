from logging import Logger

import trio
from trio.abc import Instrument
from trio.lowlevel import Task


class LogBlockingTaskInstrument(Instrument):
    """A :class:`trio.abc.Instrument` loging a warning if a task doesn't yield for a
    long time.

    This is useful to detect tasks that might be blocking and prevent the event loop to
    respond to other tasks in a timely manner.

    Args:
        duration: The duration in seconds after which a warning should be logged.
        logger: The logger to use for logging the warning.
    """

    def __init__(self, duration: float, logger: Logger):
        self.duration = duration
        self.logger = logger

    def before_task_step(self, task: Task) -> None:
        assert task.custom_sleep_data is None
        task.custom_sleep_data = {"start_time": trio.current_time()}

    def after_task_step(self, task: Task) -> None:
        data = task.custom_sleep_data
        if data is not None:
            elapsed = trio.current_time() - data["start_time"]
            if elapsed > self.duration:
                self.logger.warning(
                    "Task %r didn't yield to the event loop after %.4f seconds",
                    task, elapsed
                )
            task.custom_sleep_data = None

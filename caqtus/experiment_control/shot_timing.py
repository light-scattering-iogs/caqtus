import trio

from caqtus.utils._no_public_constructor import NoPublicConstructor


class ShotTimer(metaclass=NoPublicConstructor):
    """Gives access to pseudo-real time primitives during a shot.

    This give the possibility to wait for a target time in the shot to be reached, to
    sleep for a given amount of time, or to get the elapsed time since the start of the
    shot.

    All times are relative to the start of the shot and are in seconds.
    """

    def __init__(self) -> None:
        # This class relies on the trio implementation.
        # It would need to be adapted for anyio/asyncio.
        self._start_time = trio.current_time()

    def elapsed(self) -> float:
        """Returns the elapsed time since the start of the shot."""

        return trio.current_time() - self._start_time

    async def wait_until(self, target_time: float) -> float:
        """Waits until a target time is reached.

        Args:
            target_time: The target time relative to the start of the shot.
                The target time can be in the past, in which case the function will
                return immediately.

        Returns:
            The duration waited for the target time to be reached.
            This duration can be negative if the target time is in the past.

        Warning:
            This function is not guaranteed to be precise.
            Its accuracy depends on the underlying system and the event loop load.
        """

        duration_to_sleep = target_time - self.elapsed()
        # It is safe to sleep for a negative duration, it will return immediately, but
        # with a checkpoint.
        await trio.sleep(duration_to_sleep)
        return duration_to_sleep

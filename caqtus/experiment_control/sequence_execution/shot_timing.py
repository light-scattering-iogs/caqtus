import anyio.lowlevel
import trio

from caqtus.utils._no_public_constructor import NoPublicConstructor


class ShotTimer(metaclass=NoPublicConstructor):
    """Gives access to pseudo-real time primitives during a shot.

    It gives the possibility to react at specific times during a shot.

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

        Raises:
            ValueError: If the target time is negative.

        Warning:
            This function is not guaranteed to be precise.
            Its accuracy depends on the underlying operating system and the event loop
            load.
        """

        if target_time < 0:
            raise ValueError("The target time must be positive.")

        duration_to_sleep = target_time - self.elapsed()

        if duration_to_sleep < 0:
            # We still need to await to get a checkpoint.
            await anyio.lowlevel.checkpoint()
        else:
            await trio.sleep(duration_to_sleep)
        return duration_to_sleep

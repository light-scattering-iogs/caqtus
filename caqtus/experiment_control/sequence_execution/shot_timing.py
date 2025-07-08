import anyio.lowlevel

from caqtus.utils._no_public_constructor import NoPublicConstructor


class ShotTimer:
    """Gives access to pseudo-real time primitives during a shot.

    It gives the possibility to react at specific times during a shot.

    All times are relative to the start of the shot and are in seconds.
    """

    def __init__(self) -> None:
        self._start_time = anyio.current_time()

    def elapsed(self) -> float:
        """Returns the elapsed time since the start of the shot."""

        return anyio.current_time() - self._start_time

    async def wait_until(self, target_time: float) -> float:
        """Waits until a target time is reached.

        Args:
            target_time: The target time relative to the start of the shot.
                The target time can be in the past, in which case the function will
                return immediately.

        Returns:
            The duration waited for the target time to be reached.
            This duration is positive if the target time is in the future at the moment
            of the call.
            This duration is negative if the target time is in the past at the moment of
            the call.

        Raises:
            ValueError: If the target time is negative.

        Warning:
            This function is not guaranteed to be precise.
            Its accuracy depends on the underlying operating system and the event loop
            load.
        """

        if target_time < 0:
            raise ValueError("The target time must be positive.")

        absolute_target_time = self._start_time + target_time

        absolute_current_time = anyio.current_time()
        duration_to_wait = absolute_target_time - absolute_current_time

        if duration_to_wait < 0:
            # We ensure that we go through a cancellation point even if there is no
            # wait.
            await anyio.lowlevel.checkpoint()
        else:
            await anyio.sleep_until(absolute_target_time)
        return duration_to_wait

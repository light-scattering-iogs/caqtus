from typing import SupportsFloat

_ns = 1e-9


def duration_to_ticks(duration: SupportsFloat, time_step: int) -> int:
    """Returns the nearest number of ticks for a given duration and time step.

    Args:
        duration: The duration in seconds.
        time_step: The time step in nanoseconds.
    """

    rounded = round(float(duration) / time_step / _ns)
    if not isinstance(rounded, int):
        raise TypeError(f"Expected integer number of ticks, got {rounded}")
    return rounded

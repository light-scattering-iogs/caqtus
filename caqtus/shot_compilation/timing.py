import decimal
from typing import SupportsFloat, TYPE_CHECKING

if TYPE_CHECKING:
    from caqtus.device.sequencer import TimeStep

_ns = decimal.Decimal("1e-9")


def duration_to_ticks(duration: SupportsFloat, time_step: "TimeStep") -> int:
    """Returns the nearest number of ticks for a given duration and time step.

    Args:
        duration: The duration in seconds.
        time_step: The time step in nanoseconds.
    """

    dt = time_step * _ns

    rounded = round(float(duration) / float(dt))
    if not isinstance(rounded, int):
        raise TypeError(f"Expected integer number of ticks, got {rounded}")
    return rounded

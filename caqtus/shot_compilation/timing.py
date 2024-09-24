import decimal
import math
from itertools import accumulate
from typing import Iterable, Sequence, NewType

Time = NewType("Time", decimal.Decimal)
"""A type for representing time in seconds.

It uses a decimal.Decimal to represent time in seconds to avoid floating point errors.
"""


ps = decimal.Decimal("1e-12")


def to_time(value: decimal.Decimal | float | str) -> Time:
    """Converts a value to a Time object.

    Args:
        value: The value to convert to a Time object.

    Returns:
        A Time object representing the value in seconds, rounded to the picosecond.
    """

    return Time(decimal.Decimal(value).quantize(ps))


def to_time_bounds(durations: Iterable[float]) -> Sequence[Time]:
    """Converts an iterable of durations to an iterable of Time objects.

    Args:
        durations: An iterable of durations in seconds.

    Returns:
        An iterable of Time objects representing the durations in seconds.
    """

    return [to_time(duration) for duration in durations]


def get_step_bounds(step_durations: Iterable[Time]) -> Sequence[Time]:
    """Returns the time at which each step starts from their durations.

    For an iterable of step durations [d_0, d_1, ..., d_n], the step starts are
    [0, d_0, d_0 + d_1, ..., d_0 + ... + d_n]. It has one more element than the
    iterable of step durations, with the last element being the total duration.
    """

    zero = Time(decimal.Decimal(0))
    return [zero] + list((accumulate(step_durations)))


def start_tick(start_time: Time, time_step: Time) -> int:
    """Returns the included first tick index of the step starting at start_time."""

    return math.ceil(start_time / time_step)


def stop_tick(stop_time: Time, time_step: Time) -> int:
    """Returns the excluded last tick index of the step ending at stop_time."""

    return math.ceil(stop_time / time_step)


def number_ticks(start_time: Time, stop_time: Time, time_step: Time) -> int:
    """Returns the number of ticks between start_time and stop_time.

    Args:
        start_time: The start time in seconds.
        stop_time: The stop time in seconds.
        time_step: The time step in seconds.
    """

    return stop_tick(stop_time, time_step) - start_tick(start_time, time_step)

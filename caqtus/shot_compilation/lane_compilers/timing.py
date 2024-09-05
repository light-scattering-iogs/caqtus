"""Contains functions for computing timing of a sequencer."""

import decimal
import math
from collections.abc import Iterable, Sequence
from itertools import accumulate
from typing import NewType

Time = NewType("Time", decimal.Decimal)
"""A type for representing time in seconds.

It uses a decimal.Decimal to represent time in seconds to avoid floating point errors.
"""

ns = decimal.Decimal("1e-9")


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


def get_step_bounds(step_durations: Iterable[Time]) -> Sequence[Time]:
    """Returns the time at which each step starts from their durations.

    For an iterable of step durations [d_0, d_1, ..., d_n], the step starts are
    [0, d_0, d_0 + d_1, ..., d_0 + ... + d_n]. It has one more element than the
    iterable of step durations, with the last element being the total duration.
    """

    zero = Time(decimal.Decimal(0))
    return [zero] + list((accumulate(step_durations)))

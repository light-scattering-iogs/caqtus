import decimal
from typing import NewType

from caqtus.shot_compilation.timing import start_tick, stop_tick, number_ticks, Time

__all__ = [
    "TimeStep",
    "start_time_step",
    "stop_time_step",
    "number_time_steps",
    "number_time_steps_between",
]

TimeStep = NewType("TimeStep", decimal.Decimal)
"""A type alias that represents the duration of a time step in nanoseconds.

A time step is represented as a decimal number to avoid floating point errors.
"""

ns = Time(decimal.Decimal("1e-9"))


def start_time_step(start_time: Time, time_step: TimeStep) -> int:
    """Returns the time of the step starting at start_time."""

    return start_tick(start_time, Time(time_step * ns))


def stop_time_step(stop_time: Time, time_step: TimeStep) -> int:
    """Returns the time of the step ending at stop_time."""

    return stop_tick(stop_time, Time(time_step * ns))


def number_time_steps(duration: Time, time_step: TimeStep) -> int:
    """Returns the number of ticks covering the given duration.

    Args:
        duration: The duration in seconds.
        time_step: The time step in seconds.
    """

    return number_ticks(Time(decimal.Decimal(0)), duration, Time(time_step * ns))


def number_time_steps_between(
    start_time: Time, stop_time: Time, time_step: TimeStep
) -> int:
    """Returns the number of ticks covering the given duration.

    Args:
        start_time: The start time in seconds.
        stop_time: The stop time in seconds.
        time_step: The time step in seconds.
    """

    return number_ticks(start_time, stop_time, Time(time_step * ns))

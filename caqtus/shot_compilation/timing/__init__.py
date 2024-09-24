"""Contains utility functions for defining and discretizing times."""

from ._timing import (
    Time,
    to_time,
    to_time_bounds,
    get_step_bounds,
    start_tick,
    stop_tick,
    number_ticks,
    ps,
)

__all__ = [
    "Time",
    "to_time",
    "to_time_bounds",
    "get_step_bounds",
    "start_tick",
    "stop_tick",
    "number_ticks",
    "ps",
]

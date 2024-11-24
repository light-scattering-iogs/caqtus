from __future__ import annotations

from typing import SupportsFloat

import numpy as np
from ._empty import Empty
from ._pattern import Pattern, pattern


def ramp(
    start: SupportsFloat, stop: SupportsFloat, length: int
) -> Ramp | Empty | Pattern[np.float64]:
    """Creates a linear ramp between two values."""

    if length >= 2:
        return Ramp(np.float64(start), np.float64(stop), length)
    elif length == 0:
        return Empty()
    elif length == 1:
        return pattern([float(start)])
    else:
        raise ValueError("The length must positive.")


class Ramp:
    """Represents a linear ramp between two values.

    Use the :func:`ramp` function to create an instance of this class, do not
    instantiate it directly.
    """

    __slots__ = ("_start", "_stop", "_length")

    def __init__(self, start: np.float64, stop: np.float64, length: int):
        self._start = start
        self._stop = stop
        self._length = length
        assert length >= 2

    @property
    def start(self) -> np.float64:
        return self._start

    @property
    def stop(self) -> np.float64:
        return self._stop

    def __repr__(self) -> str:
        return f"Ramp({self._start}, {self._stop}, {self._length})"

    def __str__(self) -> str:
        return f"ramp({self._start}, {self._stop}, {self._length})"

    def __len__(self) -> int:
        return self._length

    @staticmethod
    def dtype() -> np.dtype[np.float64]:
        return np.dtype(np.float64)

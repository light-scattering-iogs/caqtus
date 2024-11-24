from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, overload

import numpy as np
from numpy.typing import NDArray, ArrayLike

from ._typing import DataT
from ._empty import Empty


@overload
def pattern(values: Sequence[bool]) -> Pattern[np.bool] | Empty: ...  # type: ignore[reportOverlappingOverload]


@overload
def pattern(values: Sequence[int]) -> Pattern[np.int64] | Empty: ...


@overload
def pattern(values: Sequence[float]) -> Pattern[np.float64] | Empty: ...


def pattern(values: ArrayLike) -> Pattern | Empty:
    """Create a pattern from a sequence of values.

    Raises:
        ValueError: If the values are empty or not one-dimensional.
    """

    values = np.array(values)
    if values.ndim != 1:
        raise ValueError("The values must be a one-dimensional array.")
    if len(values) == 0:
        return Empty()
    return Pattern(values)


class Pattern(Generic[DataT]):
    """A sequence of arbitrary values.

    This allows to represent a series of values in the most explicit way possible.
    However, whenever possible, it is recommended to use a more specific instruction.

    To create a pattern, use the :func:`pattern` function and not the constructor
    directly.
    """

    __slots__ = ("_array",)
    __match_args__ = ("values",)

    def __init__(self, values: NDArray[DataT]):
        assert isinstance(values, np.ndarray)
        assert values.ndim == 1
        assert len(values) > 0
        self._array = values

    @property
    def values(self) -> NDArray[DataT]:
        """The values in the pattern.

        The array is guaranteed to have exactly one dimension and at least one element.

        Warning:
            Modifying the returned array will modify the underlying pattern and is
            discouraged.
        """

        return self._array

    def dtype(self) -> np.dtype[DataT]:
        """The data type of the values in the pattern."""

        return self._array.dtype

    def __repr__(self) -> str:
        return f"Pattern({self._array!r})"

    def __str__(self) -> str:
        return str(self._array)

    def __len__(self) -> int:
        return len(self._array)

    def __getitem__(self, index: int) -> DataT:
        return self._array[index]

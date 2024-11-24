from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, overload, Self

import numpy as np
from numpy.typing import NDArray, ArrayLike

from ._empty import Empty
from ._repeated import Repeated
from ._typing import DataT_co


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


class Pattern(Generic[DataT_co]):
    """A sequence of arbitrary values.

    This allows to represent a series of values in the most explicit way possible.
    However, whenever possible, it is recommended to use a more specific instruction.

    To create a pattern, use the :func:`pattern` function and not the constructor
    directly.
    """

    __slots__ = ("_array",)
    __match_args__ = ("values",)

    def __init__(self, values: NDArray[DataT_co]):
        assert isinstance(values, np.ndarray)
        assert values.ndim == 1
        assert len(values) > 0
        self._array = values

    @property
    def values(self) -> NDArray[DataT_co]:
        """The values in the pattern.

        The array is guaranteed to have exactly one dimension and at least one element.

        Warning:
            Modifying the returned array will modify the underlying pattern and is
            discouraged.
        """

        return self._array

    def dtype(self) -> np.dtype[DataT_co]:
        """The data type of the values in the pattern."""

        return self._array.dtype

    def __repr__(self) -> str:
        return f"Pattern({self._array!r})"

    def __str__(self) -> str:
        return str(self._array)

    def __len__(self) -> int:
        return len(self._array)

    def __eq__(self, other) -> bool:
        if isinstance(other, Pattern):
            return np.array_equal(self._array, other._array)
        else:
            return False

    @overload
    def __getitem__(self, item: int, /) -> DataT_co: ...

    @overload
    def __getitem__(self, item: slice, /) -> Self | Empty: ...

    def __getitem__(self, item: int | slice, /) -> DataT_co | Self | Empty:
        if isinstance(item, slice):
            sliced = self._array[item]
            if len(sliced) == 0:
                return Empty()
            return self.__class__(sliced)
        else:
            return self._array[item]

    def __add__(self, other: Empty | Self) -> Self:
        if isinstance(other, Empty):
            return self
        return self.__class__(np.concatenate([self._array, other._array]))

    def __mul__(self, other: int) -> Repeated[Self] | Self | Empty:
        if other >= 2:
            return Repeated(other, self)
        elif other == 1:
            return self
        elif other == 0:
            return Empty()
        else:
            raise ValueError("The number of repetitions must be non-negative.")

    def __rmul__(self, other: int) -> Repeated[Self] | Self | Empty:
        return self.__mul__(other)

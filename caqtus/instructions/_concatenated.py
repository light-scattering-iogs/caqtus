from __future__ import annotations

from typing import Generic, overload, Self

import numpy as np
from typing_extensions import TypeVar

from ._empty import Empty
from ._indexing import (
    Indexable,
    _normalize_index,
    SupportsSlicing,
    _normalize_slice,
)
from ._repeated import Repeated
from ._typing import SubInstruction, HasDType, DataT_co, Addable, InstrT_co, InstrT_inv

LeftInstrT = TypeVar(
    "LeftInstrT", bound=SubInstruction, covariant=True, default=SubInstruction
)
RightInstrT = TypeVar(
    "RightInstrT", bound=SubInstruction, covariant=True, default=SubInstruction
)


class Concatenated(Generic[LeftInstrT, RightInstrT]):
    """The concatenation of two instructions.

    Use the `+` operator to create an instance of this class, do not instantiate it
    directly.
    """

    __slots__ = ("_left", "_right", "_length")
    __match_args__ = ("left", "right")

    def __init__(self, left: LeftInstrT, right: RightInstrT) -> None:
        self._left = left
        self._right = right
        self._length = len(left) + len(right)

    @property
    def left(self) -> LeftInstrT:
        """The left instruction."""

        return self._left

    @property
    def right(self) -> RightInstrT:
        """The right instruction."""

        return self._right

    def __repr__(self) -> str:
        return f"Concatenated({self._left!r}, {self._right!r})"

    def __str__(self) -> str:
        return f"({self._left} + {self._right})"

    def __len__(self) -> int:
        return self._length

    def dtype[
        DataT: (np.bool, np.int64, np.float64, np.void)
    ](self: Concatenated[HasDType[DataT], HasDType[DataT]]) -> np.dtype[DataT]:
        return self._left.dtype()

    @overload
    def __getitem__(
        self: Concatenated[Indexable[DataT_co], Indexable[DataT_co]], item: int
    ) -> DataT_co: ...

    @overload
    def __getitem__(
        self: Concatenated[
            SupportsSlicing[Addable[InstrT_inv, InstrT_co]],
            SupportsSlicing[InstrT_inv],
        ],
        item: slice,
    ) -> InstrT_co | InstrT_inv | Empty: ...

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self._get_slice(item)  # type: ignore[reportAttributeAccessIssue]
        else:
            return self._get_index(item)  # type: ignore[reportAttributeAccessIssue]

    def _get_slice(
        self: Concatenated[
            SupportsSlicing[Addable[InstrT_inv, InstrT_co]],
            SupportsSlicing[InstrT_inv],
        ],
        item: slice,
    ) -> InstrT_co | InstrT_inv | Empty:
        start, stop, step = _normalize_slice(item, len(self))
        if step != 1:
            raise NotImplementedError("Slicing with a step is not supported")
        left_slice = self._left[
            min(start, len(self._left)) : min(stop, len(self._left))
        ]
        right_slice = self._right[
            max(start - len(self._left), 0) : max(stop - len(self._left), 0)
        ]
        return left_slice + right_slice

    def _get_index(
        self: Concatenated[Indexable[DataT_co], Indexable[DataT_co]], item: int
    ) -> DataT_co:
        item = _normalize_index(item, len(self))
        if item < len(self._left):
            return self._left[item]
        else:
            return self._right[item - len(self._left)]

    def __mul__(self, other: int) -> Repeated[Self] | Self | Empty:
        if other >= 2:
            return Repeated(other, self)
        elif other == 1:
            return self
        elif other == 0:
            return Empty()
        else:
            raise ValueError("Cannot multiply by a negative number")

    def __rmul__(self, other: int) -> Repeated[Self] | Self | Empty:
        return self.__mul__(other)

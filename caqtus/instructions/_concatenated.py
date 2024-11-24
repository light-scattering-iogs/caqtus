from __future__ import annotations

from typing import Generic, overload

import numpy as np
from typing_extensions import TypeVar

from ._indexing import Indexable, _normalize_index
from ._typing import SubInstruction, HasDType, DataT_co

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
        self,
        item: slice,
    ) -> None: ...

    def __getitem__(self, item):
        if isinstance(item, slice):
            pass
        else:
            return self._get_index(item)  # type: ignore[reportAttributeAccessIssue]

    def _get_index(
        self: Concatenated[Indexable[DataT_co], Indexable[DataT_co]], item: int
    ) -> DataT_co:
        item = _normalize_index(item, len(self))
        if item < len(self._left):
            return self._left[item]
        else:
            return self._right[item - len(self._left)]

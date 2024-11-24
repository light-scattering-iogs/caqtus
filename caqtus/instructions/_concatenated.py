from __future__ import annotations

from typing import Generic

import numpy as np
from typing_extensions import TypeVar

from ._typing import SubInstruction, HasDType, DataT

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

    def dtype(self: Concatenated[HasDType[DataT], HasDType[DataT]]) -> np.dtype[DataT]:
        return self._left.dtype()

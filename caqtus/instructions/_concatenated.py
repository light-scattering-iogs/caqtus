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
    """The concatenation of two instructions."""

    def __init__(self, left: LeftInstrT, right: RightInstrT) -> None:
        self._left = left
        self._right = right

    @property
    def left(self) -> LeftInstrT:
        """The left instruction."""

        return self._left

    @property
    def right(self) -> RightInstrT:
        """The right instruction."""

        return self._right

    def dtype(self: Concatenated[HasDType[DataT], HasDType[DataT]]) -> np.dtype[DataT]:
        return self._left.dtype()

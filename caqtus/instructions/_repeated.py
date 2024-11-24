from __future__ import annotations

import math
from typing import Generic, Self

import numpy as np
from typing_extensions import TypeVar

from ._empty import Empty
from ._typing import SubInstruction, HasDType, DataT_co
from ._indexing import Indexable, _normalize_index, Sliceable, _normalize_slice

InstrT = TypeVar("InstrT", bound=SubInstruction, covariant=True, default=SubInstruction)


class Repeated(Generic[InstrT]):
    """Represents the repetition of an instruction.

    Use the `*` operator to create an instance of this class, do not instantiate it
    directly.
    """

    __slots__ = ("_instruction", "_count", "_length")
    __match_args__ = ("count", "instruction")

    def __init__(self, count: int, instruction: InstrT) -> None:
        assert count >= 2
        self._instruction = instruction
        self._count = count
        self._length = len(instruction) * count

    @property
    def instruction(self) -> InstrT:
        """The instruction to repeat."""

        return self._instruction

    @property
    def count(self) -> int:
        """The number of times to repeat the instruction.

        It is guaranteed to be at least 2.
        """

        return self._count

    def __repr__(self) -> str:
        return f"Repeated({self._count}, {self._instruction!r})"

    def __str__(self) -> str:
        return f"({self._count} * {self._instruction})"

    def __len__(self) -> int:
        return self._length

    def dtype(self: Repeated[HasDType[DataT_co]]) -> np.dtype[DataT_co]:
        return self._instruction.dtype()

    def _get_index(self: Repeated[Indexable[DataT_co]], index: int) -> DataT_co:
        index = _normalize_index(index, len(self))
        _, r = divmod(index, len(self._instruction))
        return self._instruction[r]

    def _get_slice(self, slice_: slice):
        start, stop, step = _normalize_slice(slice_, len(self))
        if step != 1:
            raise NotImplementedError
        length = len(self._instruction)
        first_repetition = math.ceil(start / length)
        last_repetition = math.floor(stop / length)
        if first_repetition > last_repetition:
            return self._instruction[
                start - first_repetition * length : stop - first_repetition * length
            ]
        else:
            previous_repetition = math.floor(start / length)
            prepend = self._instruction[
                start
                - previous_repetition
                * length : (first_repetition - previous_repetition)
                * length
            ]
            middle = self._instruction * (last_repetition - first_repetition)
            append = self._instruction[: stop - last_repetition * length]
            return prepend + middle + append

    def __mul__(self, other: int) -> Self | Empty:
        if other >= 1:
            return self.__class__(self._count * other, self._instruction)
        elif other == 0:
            return Empty()
        else:
            raise ValueError("The repetition count cannot be negative")

    def __rmul__(self, other: int) -> Self | Empty:
        return self.__mul__(other)

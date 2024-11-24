from __future__ import annotations

from typing import Generic, Self, Protocol, overload

import numpy as np
from typing_extensions import TypeVar

from ._concatenated import Concatenated
from ._empty import Empty
from ._indexing import (
    Indexable,
    _normalize_index,
    SupportsSlicing,
    _normalize_slice,
)
from ._typing import SubInstruction, HasDType, DataT_co, Addable, Multipliable

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

    @overload
    def __getitem__(self: Repeated[Indexable[DataT_co]], item: int) -> DataT_co: ...

    @overload
    def __getitem__(
        self: Repeated[SupportsRepeatedSlicing[SliceR]], item: slice
    ) -> SliceR: ...

    def __getitem__(self, item):
        if isinstance(item, slice):
            return self._get_slice(item)  # type: ignore[reportAttributeAccessIssue]
        elif isinstance(item, int):
            return self._get_index(item)  # type: ignore[reportAttributeAccessIssue]
        else:
            raise TypeError("Invalid argument type")

    def _get_index(self: Repeated[Indexable[DataT_co]], index: int) -> DataT_co:
        index = _normalize_index(index, len(self))
        _, r = divmod(index, len(self._instruction))
        return self._instruction[r]

    def _get_slice(
        self: Repeated[SupportsRepeatedSlicing[SliceR]],
        slice_: slice,
    ) -> SliceR:
        start, stop, step = _normalize_slice(slice_, len(self))
        if step != 1:
            raise NotImplementedError

        length = len(self._instruction)

        slice_length = stop - start
        q, r = divmod(slice_length, length)
        local_start = start % length

        left = self._instruction[local_start:]
        right = self._instruction[:local_start]

        rearranged_instruction = left + right
        result = rearranged_instruction * q + rearranged_instruction[:r]
        return result

    def __mul__(self, other: int) -> Self | Empty:
        if other >= 1:
            return self.__class__(self._count * other, self._instruction)
        elif other == 0:
            return Empty()
        else:
            raise ValueError("The repetition count cannot be negative")

    def __rmul__(self, other: int) -> Self | Empty:
        return self.__mul__(other)

    def __add__[
        T: SubInstruction
    ](self, other: Empty | T) -> Self | Concatenated[Self, T]:
        if isinstance(other, Empty):
            return self
        return Concatenated(self, other)


SliceR = TypeVar("SliceR", bound=SubInstruction, covariant=True, default=SubInstruction)
SliceT = TypeVar("SliceT", bound=SubInstruction, default=SubInstruction)


class CanAddMultiplicationWithSlice(
    SupportsSlicing[SliceT],
    Multipliable[Addable[SliceT, SliceR]],
    Protocol[SliceT, SliceR],
):
    pass


SelfAddableResultT = TypeVar(
    "SelfAddableResultT",
    covariant=True,
    bound=SubInstruction,
    default=SubInstruction,
)


class SelfAddable(SubInstruction, Protocol[SelfAddableResultT]):
    def __add__(self, other: Self) -> SelfAddableResultT: ...


class SupportsRepeatedSlicing(
    SupportsSlicing[SelfAddable[CanAddMultiplicationWithSlice[SubInstruction, SliceR]]],
    Protocol[SliceR],
):
    pass

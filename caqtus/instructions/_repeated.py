from __future__ import annotations

from typing import Generic

import numpy as np
from typing_extensions import TypeVar

from ._typing import SubInstruction, HasDType

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

    def dtype[DataT: np.generic](self: Repeated[HasDType[DataT]]) -> np.dtype[DataT]:
        return self._instruction.dtype()

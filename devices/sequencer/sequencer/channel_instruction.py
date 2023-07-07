from collections.abc import Sequence
from typing import TypeVar, Protocol

import numpy as np
from numpy.typing import DTypeLike

ChannelType = TypeVar("ChannelType", bound=DTypeLike, covariant=True)


class ChannelInstruction(Protocol[ChannelType]):
    def __len__(self) -> int:
        """Duration of the instruction in number of clock cycles."""
        ...


class Pattern(ChannelInstruction[ChannelType]):
    """A sequence of values to be output on a channel."""

    def __init__(self, values: Sequence[ChannelType]) -> None:
        self.values = np.array(values)

    def __len__(self) -> int:
        return len(self.values)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.values!r})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.values!s})"


class ConsecutiveInstructions(ChannelInstruction[ChannelType]):
    """A sequence of instructions to be executed consecutively.

    Attributes:
        instructions: The instructions to be executed
    """

    def __init__(self, instructions: Sequence[ChannelInstruction[ChannelType]]) -> None:
        self.instructions = instructions

    def __len__(self) -> int:
        return sum(len(instruction) for instruction in self.instructions)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.instructions!r})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.instructions!s})"


class Repeat(ChannelInstruction[ChannelType]):
    """Repeat a single instruction a given number of times.

    Attributes:
        instruction: The instruction to be repeated.
        number_repetitions: The number of times to repeat the instruction.
    """

    def __init__(
        self, instruction: ChannelInstruction[ChannelType], number_repetitions: int
    ) -> None:
        self.instruction = instruction
        self.number_repetitions = number_repetitions

    def __len__(self) -> int:
        return len(self.instruction) * self.number_repetitions

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.instruction!r}, {self.number_repetitions!r})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.instruction!s}, {self.number_repetitions!s})"

from abc import ABC
from collections.abc import Sequence
from typing import TypeVar, Generic, Any
from .splittable import Splittable

import numpy as np
from numpy.typing import DTypeLike

ChannelType = TypeVar("ChannelType", bound=DTypeLike, covariant=True)


class ChannelInstruction(Splittable, Generic[ChannelType], ABC):
    def _check_length_valid(self) -> None:
        if len(self) < 0:
            raise ValueError(f"Invalid instruction length {len(self)}.")
        elif len(self) == 0:
            raise ValueError("Instruction must have at least one clock cycle.")


class Pattern(ChannelInstruction[ChannelType]):
    """A sequence of values to be output on a channel."""

    def __init__(self, values: Sequence[ChannelType]) -> None:
        self.values = np.array(values)

    @property
    def values(self) -> np.ndarray[Any, ChannelType]:
        return self._values

    @values.setter
    def values(self, values: np.ndarray[Any, ChannelType]) -> None:
        self._values = values
        self._check_length_valid()

    def __len__(self) -> int:
        return len(self.values)

    def split(
        self, split_index: int
    ) -> tuple["ChannelInstruction[ChannelType]", "ChannelInstruction[ChannelType]"]:
        self._check_split_valid(split_index)
        return Pattern(self.values[:split_index]), Pattern(self.values[split_index:])

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
        self.instructions = list(instructions)

    @property
    def instructions(self) -> list[ChannelInstruction[ChannelType]]:
        return self._instructions

    @instructions.setter
    def instructions(self, instructions: list[ChannelInstruction[ChannelType]]):
        self._instructions = list(instructions)
        self._instruction_starts = np.cumsum(
            [0] + [len(instruction) for instruction in instructions]
        )
        self._check_length_valid()

    def __len__(self) -> int:
        return sum(len(instruction) for instruction in self.instructions)

    def split(
        self, split_index: int
    ) -> tuple["ChannelInstruction[ChannelType]", "ChannelInstruction[ChannelType]"]:
        self._check_split_valid(split_index)

        instruction_index = self._find_instruction_index(split_index)
        instruction_to_split = self.instructions[instruction_index]

        if split_index == self._instruction_starts[instruction_index]:
            a = []
            b = [instruction_to_split]
        elif split_index == self._instruction_starts[instruction_index] + len(
            instruction_to_split
        ):
            a = [instruction_to_split]
            b = []
        else:
            x, y = instruction_to_split.split(
                split_index - self._instruction_starts[instruction_index]
            )
            a, b = [x], [y]

        first_part = ConsecutiveInstructions(self.instructions[:instruction_index] + a)
        second_part = ConsecutiveInstructions(
            b + self.instructions[instruction_index + 1 :]
        )
        return first_part, second_part

    def _find_instruction_index(self, time: int) -> int:
        """Find the index of the instruction active at the given time index."""

        if time < 0:
            raise ValueError(f"Time index must be non-negative, got {time}.")
        if time >= len(self):
            raise ValueError(f"Time index must be less than {len(self)}, got {time}.")

        return int(np.searchsorted(self._instruction_starts, time, side="right") - 1)

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
        self._instruction = instruction
        self._number_repetitions = number_repetitions
        self._check_length_valid()

    @property
    def instruction(self) -> ChannelInstruction[ChannelType]:
        return self._instruction

    @instruction.setter
    def instruction(self, instruction: ChannelInstruction[ChannelType]) -> None:
        self._instruction = instruction
        self._check_length_valid()

    @property
    def number_repetitions(self) -> int:
        return self._number_repetitions

    @number_repetitions.setter
    def number_repetitions(self, number_repetitions: int) -> None:
        self._number_repetitions = number_repetitions
        self._check_length_valid()

    def __len__(self) -> int:
        return len(self.instruction) * self.number_repetitions

    def split(
        self, split_index: int
    ) -> tuple["ChannelInstruction[ChannelType]", "ChannelInstruction[ChannelType]"]:
        self._check_split_valid(split_index)
        instruction_length = len(self.instruction)
        first_part: ChannelInstruction[ChannelType]
        second_part: ChannelInstruction[ChannelType]
        if split_index % instruction_length == 0:
            first_part = Repeat(self.instruction, split_index // instruction_length)
            second_part = Repeat(
                self.instruction,
                self.number_repetitions - split_index // instruction_length,
            )
        else:
            first = []
            second = []
            if split_index // instruction_length > 0:
                first.append(
                    Repeat(self.instruction, split_index // instruction_length)
                )
            if split_index // instruction_length + 1 < self.number_repetitions:
                second.append(
                    Repeat(
                        self.instruction,
                        self.number_repetitions - split_index // instruction_length - 1,
                    )
                )
            s2, s3 = self.instruction.split(split_index % instruction_length)
            first.append(s2)
            second.append(s3)
            first_part = ConsecutiveInstructions(first)
            second_part = ConsecutiveInstructions(second)
        return first_part, second_part

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.instruction!r},"
            f" {self.number_repetitions!r})"
        )

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}({self.instruction!s},"
            f" {self.number_repetitions!s})"
        )

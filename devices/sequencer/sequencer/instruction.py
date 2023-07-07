from abc import ABC
from typing import TypeVar, Generic, Iterable, Self

import numpy as np

from sequencer.splittable import Splittable

PatternType = TypeVar("PatternType", bound=Splittable, covariant=True)

SplitResult = TypeVar("SplitResult", bound="Instruction", covariant=True)


class Instruction(Splittable[SplitResult], Generic[PatternType, SplitResult], ABC):
    pass


class ConsecutiveInstructions(
    Instruction[PatternType, Instruction[PatternType, SplitResult]]
):
    """A sequence of instructions to be executed consecutively.

    Attributes:
        instructions: The instructions to be executed
    """

    def __init__(
        self, instructions: Iterable[Instruction[PatternType, SplitResult]]
    ) -> None:
        self.instructions = list(instructions)

    @property
    def instructions(self) -> list[Instruction[PatternType, SplitResult]]:
        return self._instructions

    @instructions.setter
    def instructions(
        self, instructions: list[Instruction[PatternType, SplitResult]]
    ) -> None:
        self._instructions = list(instructions)
        self._instruction_starts = np.cumsum(
            [0] + [len(instruction) for instruction in instructions]
        )
        self._check_length_valid()

    def __len__(self) -> int:
        return sum(len(instruction) for instruction in self.instructions)

    def split(self, split_index: int) -> tuple[Self, Self]:
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
        cls = type(self)
        first_part = cls(self.instructions[:instruction_index] + a)
        second_part = cls(b + self.instructions[instruction_index + 1 :])
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


class Repeat(Instruction[PatternType, Instruction[PatternType, SplitResult]]):
    """Repeat a single instruction a given number of times.

    Attributes:
        instruction: The instruction to be repeated.
        number_repetitions: The number of times to repeat the instruction.
    """

    def __init__(
        self,
        instruction: Instruction[PatternType, SplitResult],
        number_repetitions: int,
    ) -> None:
        self._instruction = instruction
        self._number_repetitions = number_repetitions
        self._check_length_valid()

    @property
    def instruction(self) -> Instruction[PatternType, SplitResult]:
        return self._instruction

    @instruction.setter
    def instruction(self, instruction: Instruction[PatternType, SplitResult]) -> None:
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
    ) -> tuple[
        Instruction[PatternType, SplitResult], Instruction[PatternType, SplitResult]
    ]:
        self._check_split_valid(split_index)
        instruction_length = len(self.instruction)
        first_part: Instruction[PatternType, SplitResult]
        second_part: Instruction[PatternType, SplitResult]
        if split_index % instruction_length == 0:
            first_part = Repeat[PatternType, SplitResult](
                self.instruction, split_index // instruction_length
            )
            second_part = Repeat[PatternType, SplitResult](
                self.instruction,
                self.number_repetitions - split_index // instruction_length,
            )
        else:
            first: list[Instruction[PatternType, SplitResult]] = []
            second: list[Instruction[PatternType, SplitResult]] = []
            if split_index // instruction_length > 0:
                first.append(
                    Repeat[PatternType, SplitResult](
                        self.instruction, split_index // instruction_length
                    )
                )
            if split_index // instruction_length + 1 < self.number_repetitions:
                second.append(
                    Repeat[PatternType, SplitResult](
                        self.instruction,
                        self.number_repetitions - split_index // instruction_length - 1,
                    )
                )
            s2, s3 = self.instruction.split(split_index % instruction_length)
            first.append(s2)
            second.append(s3)
            first_part = ConsecutiveInstructions[PatternType, SplitResult](first)
            second_part = ConsecutiveInstructions[PatternType, SplitResult](second)
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

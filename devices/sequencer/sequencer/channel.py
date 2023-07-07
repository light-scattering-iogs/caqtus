from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Self, Iterable

import numpy as np

from .splittable import Splittable

ChannelType = TypeVar("ChannelType", bound=np.dtype)


class ChannelInstruction(
    Splittable["ChannelInstruction[ChannelType]"],
    Generic[ChannelType],
    ABC,
):
    """Base class to describe the output sequence of a channel."""

    @abstractmethod
    def flatten(self) -> "ChannelPattern[ChannelType]":
        """Flatten the instruction into a single pattern."""

        raise NotImplementedError


class ChannelPattern(ChannelInstruction[ChannelType]):
    """A sequence of values to be output on a channel."""

    def __init__(self, values: Iterable[ChannelType]) -> None:
        self._values: np.ndarray[Any, ChannelType] = np.array(values)  # type: ignore
        self._check_length_valid()

    @property
    def values(self) -> np.ndarray[Any, ChannelType]:
        return self._values

    def __len__(self) -> int:
        return len(self.values)

    def split(self, split_index: int) -> tuple[Self, Self]:
        self._check_split_valid(split_index)
        cls = type(self)
        return cls(self.values[:split_index]), cls(self.values[split_index:])

    def flatten(self) -> Self:
        return self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.values!r})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.values!s})"

    def __eq__(self, other):
        if not isinstance(other, ChannelPattern):
            return NotImplemented
        return np.array_equal(self.values, other.values)


class Concatenate(ChannelInstruction[ChannelType]):
    """A sequence of instructions to be executed consecutively.

    Attributes:
        instructions: The instructions to be executed
    """

    def __init__(
        self,
        instructions: Iterable[ChannelInstruction[ChannelType]],
    ) -> None:
        self._instructions = tuple(instructions)
        self._instruction_starts = np.cumsum(
            [0] + [len(instruction) for instruction in instructions]
        )
        self._check_length_valid()

    @property
    def instructions(self) -> tuple[ChannelInstruction[ChannelType], ...]:
        return self._instructions

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
        first_part = cls(list(self.instructions[:instruction_index]) + a)
        second_part = cls(b + list(self.instructions[instruction_index + 1 :]))
        return first_part, second_part

    def _find_instruction_index(self, time: int) -> int:
        """Find the index of the instruction active at the given time index."""

        if time < 0:
            raise ValueError(f"Time index must be non-negative, got {time}.")
        if time >= len(self):
            raise ValueError(f"Time index must be less than {len(self)}, got {time}.")

        return int(np.searchsorted(self._instruction_starts, time, side="right") - 1)

    def flatten(self) -> ChannelPattern[ChannelType]:
        return ChannelPattern(
            np.concatenate(
                [instruction.flatten().values for instruction in self.instructions]
            )
        )

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

    def flatten(self) -> "ChannelPattern[ChannelType]":
        return ChannelPattern(
            np.tile(self.instruction.flatten().values, self.number_repetitions)
        )

    def __init__(
        self,
        instruction: ChannelInstruction[ChannelType],
        number_repetitions: int,
    ) -> None:
        self._instruction = instruction
        self._number_repetitions = number_repetitions
        self._check_length_valid()

    @property
    def instruction(self) -> ChannelInstruction[ChannelType]:
        return self._instruction

    @property
    def number_repetitions(self) -> int:
        return self._number_repetitions

    def __len__(self) -> int:
        return len(self.instruction) * self.number_repetitions

    def split(
        self, split_index: int
    ) -> tuple[ChannelInstruction[ChannelType], ChannelInstruction[ChannelType],]:
        self._check_split_valid(split_index)
        instruction_length = len(self.instruction)
        cls = type(self)
        if split_index % instruction_length == 0:
            first_part = cls(self.instruction, split_index // instruction_length)
            second_part = cls(
                self.instruction,
                self.number_repetitions - split_index // instruction_length,
            )
            return first_part, second_part
        else:
            first = tuple[ChannelInstruction[ChannelType], ...]()
            second = tuple[ChannelInstruction[ChannelType], ...]()
            if split_index // instruction_length > 0:
                first = first + (
                    cls(self.instruction, split_index // instruction_length),
                )
            if split_index // instruction_length + 1 < self.number_repetitions:
                second = (
                    cls(
                        self.instruction,
                        self.number_repetitions - split_index // instruction_length - 1,
                    ),
                ) + second
            s2, s3 = self.instruction.split(split_index % instruction_length)
            first = first + (s2,)
            second = (s3,) + second
            first_part = Concatenate[ChannelType](first)
            second_part = Concatenate[ChannelType](second)
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

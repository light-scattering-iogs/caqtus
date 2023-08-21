from abc import ABC, abstractmethod
from functools import cached_property
from typing import TypeVar, Generic, Any, Self, Iterable, Callable

import numpy as np
from attr import define

from .splittable import Splittable

ChannelType = TypeVar("ChannelType", covariant=True)


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

    @abstractmethod
    def __eq__(self, other) -> bool:
        """Equality comparison.

        Two instructions are equal if they are recursively equal. Two instructions that only satisfy
        a.flatten() == b.flatten() are not equal.
        """

        raise NotImplementedError

    def __add__(self, other) -> "ChannelInstruction[ChannelType]":
        if isinstance(other, ChannelInstruction):
            return self.join([self, other], dtype=self.dtype)
        else:
            raise TypeError(f"Can't concatenate {type(self)} and {type(other)}.")

    def __mul__(self, other: int) -> "ChannelInstruction[ChannelType]":
        multiplier = int(other)
        if multiplier < 0:
            raise ValueError("Multiplier must be positive integer.")
        elif multiplier == 0:
            return self.empty_like(self)
        elif multiplier == 1:
            return self
        else:
            return Repeat(self, multiplier)

    def __rmul__(self, other) -> "ChannelInstruction[ChannelType]":
        return self.__mul__(other)

    @classmethod
    def join(
        cls, instructions: Iterable[Self], dtype
    ) -> "ChannelInstruction[ChannelType]":
        """Concatenate multiple instructions into a single instruction.

        This method removes empty instructions from the list and flattens nested concatenations.
        """

        instructions = [
            instruction for instruction in instructions if not instruction.is_empty()
        ]
        flattened_instructions: list[ChannelInstruction[ChannelType]] = []
        for instruction in instructions:
            if isinstance(instruction, Concatenate):
                flattened_instructions.extend(instruction.instructions)
            else:
                flattened_instructions.append(instruction)

        if len(flattened_instructions) == 0:
            return cls.empty(dtype=dtype)
        elif len(flattened_instructions) == 1:
            return flattened_instructions[0]
        else:
            return Concatenate(flattened_instructions)

    def is_empty(self) -> bool:
        return len(self) == 0

    @property
    @abstractmethod
    def dtype(self) -> ChannelType:
        """Return the dtype of the channel."""

        raise NotImplementedError

    @classmethod
    def empty(cls, dtype) -> "ChannelInstruction[ChannelType]":
        """Return an empty instruction."""

        return ChannelPattern([], dtype=dtype)

    @classmethod
    def empty_like(cls, instruction: Self) -> "ChannelInstruction[ChannelType]":
        """Return an empty instruction with the same dtype as the given instruction."""

        return cls.empty(instruction.dtype)

    @abstractmethod
    def apply(
        self, fun: Callable[[ChannelType], ChannelType]
    ) -> "ChannelInstruction[ChannelType]":
        """Apply a function to each element of the instruction."""

        raise NotImplementedError


@define(init=False, eq=False)
class ChannelPattern(ChannelInstruction[ChannelType]):
    """A sequence of values to be output on a channel."""

    _values: np.ndarray[Any, ChannelType]

    def __init__(self, values: Iterable[ChannelType], dtype=None) -> None:
        self._values: np.ndarray[Any, ChannelType] = np.array(values, dtype=dtype)  # type: ignore

    @property
    def values(self) -> np.ndarray[Any, ChannelType]:
        return np.copy(self._values)

    @cached_property
    def dtype(self) -> ChannelType:
        return self._values.dtype

    def __len__(self) -> int:
        return len(self.values)

    def split(self, split_index: int):
        self._check_split_valid(split_index)

        if split_index == 0:
            return self.empty_like(self), self
        elif split_index == len(self):
            return self, self.empty_like(self)
        else:
            cls = type(self)
            return cls(self.values[:split_index], dtype=self.dtype), cls(
                self.values[split_index:], dtype=self.dtype
            )

    def flatten(self) -> Self:
        return self

    def __eq__(self, other):
        if not isinstance(other, ChannelPattern):
            return False
        return np.array_equal(self.values, other.values)

    def apply(self, fun: Callable[[ChannelType], ChannelType]):
        return type(self)(fun(self.values))


@define(init=False, eq=False)
class Concatenate(ChannelInstruction[ChannelType]):
    """A sequence of instructions to be executed consecutively."""

    _instructions: tuple[ChannelInstruction[ChannelType], ...]

    def __init__(
        self,
        instructions: Iterable[ChannelInstruction[ChannelType]],
    ) -> None:
        self._instructions = tuple(
            instruction for instruction in instructions if not instruction.is_empty()
        )
        self._instruction_starts = np.cumsum(
            [0] + [len(instruction) for instruction in instructions]
        )
        if len(self._instructions) <= 1:
            raise ValueError("Concatenation must have at least two instructions.")

    @property
    def instructions(self) -> tuple[ChannelInstruction[ChannelType], ...]:
        return self._instructions

    def __len__(self) -> int:
        return self._len

    @cached_property
    def _len(self) -> int:
        return sum(len(instruction) for instruction in self.instructions)

    def split(self, split_index: int):
        self._check_split_valid(split_index)

        if split_index == 0:
            return self.empty_like(self), self
        elif split_index == len(self):
            return self, self.empty_like(self)

        instruction_index = self._find_instruction_index(split_index)
        instruction_to_split = self.instructions[instruction_index]

        before_part, after_part = instruction_to_split.split(
            split_index - self._instruction_starts[instruction_index]
        )

        before_instruction = ChannelInstruction.join(
            self.instructions[:instruction_index] + (before_part,), dtype=self.dtype
        )
        after_instruction = ChannelInstruction.join(
            (after_part,) + self.instructions[instruction_index + 1 :], dtype=self.dtype
        )
        return before_instruction, after_instruction

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
            ),
            dtype=self.dtype,
        )

    def __str__(self) -> str:
        body = "\n".join(
            f"  {i}: {instruction!s}" for i, instruction in enumerate(self.instructions)
        )
        return f"{self.__class__.__name__}(\n{body}\n)"

    def __eq__(self, other):
        if not isinstance(other, Concatenate):
            return False
        return self.instructions == other.instructions

    @cached_property
    def dtype(self) -> ChannelType:
        return self.instructions[0].dtype

    def apply(self, fun: Callable[[ChannelType], ChannelType]):
        return type(self)([instruction.apply(fun) for instruction in self.instructions])


@define(init=False, eq=False)
class Repeat(ChannelInstruction[ChannelType]):
    """Repeat a single instruction a given number of times.

    Attributes:
        instruction: The instruction to be repeated.
        number_repetitions: The number of times to repeat the instruction. Must be greater or equal to 2.
    """

    _instruction: ChannelInstruction[ChannelType]
    _number_repetitions: int

    def __init__(
        self,
        instruction: ChannelInstruction[ChannelType],
        number_repetitions: int,
    ) -> None:
        self._instruction = instruction
        self._number_repetitions = number_repetitions
        if number_repetitions < 2:
            raise ValueError(
                f"Number of repetitions {number_repetitions} must be greater or equal"
                " to 2."
            )

    @property
    def instruction(self) -> ChannelInstruction[ChannelType]:
        return self._instruction

    @property
    def number_repetitions(self) -> int:
        return self._number_repetitions

    def __len__(self) -> int:
        return self._len

    @cached_property
    def _len(self) -> int:
        return len(self.instruction) * self.number_repetitions

    def flatten(self) -> "ChannelPattern[ChannelType]":
        return ChannelPattern(
            np.tile(self.instruction.flatten().values, self.number_repetitions),
            dtype=self.dtype,
        )

    def split(self, split_index: int):
        self._check_split_valid(split_index)
        instruction_length = len(self.instruction)

        before_part, after_part = self.instruction.split(
            split_index % instruction_length
        )

        before_repetitions = split_index // instruction_length
        before_block = self.instruction * before_repetitions
        before_instruction = ChannelInstruction.join(
            (before_block, before_part), dtype=self.dtype
        )

        if split_index % instruction_length == 0:
            after_repetitions = self.number_repetitions - before_repetitions
            after_part = after_part * 0
        else:
            after_repetitions = max(self.number_repetitions - before_repetitions - 1, 0)

        after_block = self.instruction * after_repetitions
        after_instruction = ChannelInstruction.join(
            (after_part, after_block), dtype=self.dtype
        )

        return before_instruction, after_instruction

    def __eq__(self, other):
        if not isinstance(other, Repeat):
            return False
        return (
            self.instruction == other.instruction
            and self.number_repetitions == other.number_repetitions
        )

    def __mul__(self, other):
        multiplier = int(other) * self.number_repetitions
        if multiplier == 0:
            return self.empty_like(self)
        else:
            return Repeat(self.instruction, multiplier)

    @cached_property
    def dtype(self) -> ChannelType:
        return self.instruction.dtype

    def apply(self, fun: Callable[[ChannelType], ChannelType]):
        return type(self)(self.instruction.apply(fun), self.number_repetitions)

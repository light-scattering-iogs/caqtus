from abc import ABC, abstractmethod
from collections.abc import Mapping, Iterable
from functools import cached_property
from typing import NewType, TypeVar, Any, Self

import numpy as np

from sequencer.channel import Splittable, ChannelPattern
from sequencer.channel.channel_instructions import ChannelType

ChannelLabel = NewType("ChannelLabel", int)


class SequencerInstruction(
    Splittable["SequencerInstruction"],
    ABC,
):
    """Base class to describe the output sequence of multiple channels."""

    @property
    @abstractmethod
    def channel_types(self) -> dict[ChannelLabel, ChannelType]:
        """Return the types of the channels."""

        raise NotImplementedError

    @property
    def number_channels(self) -> int:
        """Return the number of channels."""

        return len(self.channel_types)

    @abstractmethod
    def flatten(self) -> "SequencerPattern":
        """Flatten the instruction into a single pattern."""

        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other) -> bool:
        """Equality comparison.

        Two instructions are equal if they are recursively equal. Two instructions that only satisfy
        a.flatten() == b.flatten() are not equal.
        """

        raise NotImplementedError

    def __add__(self, other) -> "SequencerInstruction":
        if isinstance(other, SequencerInstruction):
            return self.join([self, other], self.channel_types)
        else:
            raise TypeError(f"Can't concatenate {type(self)} and {type(other)}.")

    def __mul__(self, other: int) -> "SequencerInstruction":
        multiplier = int(other)
        if multiplier < 0:
            raise ValueError("Multiplier must be positive integer.")
        elif multiplier == 0:
            return self.empty_like(self)
        elif multiplier == 1:
            return self
        else:
            return Repeat(self, multiplier)

    def __rmul__(self, other) -> "SequencerInstruction":
        return self.__mul__(other)

    @classmethod
    def join(
        cls,
        instructions: Iterable[Self],
        channel_types: Mapping[ChannelLabel, ChannelType],
    ) -> "SequencerInstruction":
        """Concatenate multiple instructions into a single instruction.

        This method removes empty instructions from the list and flattens nested concatenations.
        """

        instructions = [
            instruction for instruction in instructions if not instruction.is_empty()
        ]
        flattened_instructions: list[SequencerInstruction] = []
        for instruction in instructions:
            if isinstance(instruction, Concatenate):
                flattened_instructions.extend(instruction.instructions)
            else:
                flattened_instructions.append(instruction)

        if len(flattened_instructions) == 0:
            return cls.empty(channel_types)
        elif len(flattened_instructions) == 1:
            return flattened_instructions[0]
        else:
            return Concatenate(flattened_instructions)

    def is_empty(self) -> bool:
        return len(self) == 0

    @classmethod
    def empty(
        cls, channel_types: Mapping[ChannelLabel, ChannelType]
    ) -> "SequencerInstruction":
        """Return an empty instruction."""

        return SequencerPattern(
            {
                channel: ChannelPattern[Any].empty(dtype)
                for channel, dtype in channel_types.items()
            }
        )

    @classmethod
    def empty_like(cls, other: "SequencerInstruction") -> "SequencerInstruction":
        """Return an empty instruction with the same channel types as another instruction."""

        return cls.empty(other.channel_types)


class SequencerPattern(SequencerInstruction):
    """A sequence of output values for several channels."""

    def __init__(self, channel_values: Mapping[ChannelLabel, ChannelPattern]) -> None:
        if len(channel_values) == 0:
            raise ValueError("Pattern must contain at least one channel.")
        length = len(first(channel_values.values()))
        if not all(len(channel) == length for channel in channel_values.values()):
            raise ValueError("Channel patterns must have the same duration.")
        self._channel_values = dict(channel_values)

    @property
    def channel_types(self) -> dict[ChannelLabel, ChannelType]:
        return {label: pattern.dtype for label, pattern in self._channel_values.items()}

    @property
    def values(self) -> dict[ChannelLabel, ChannelPattern]:
        return dict(self._channel_values)

    def __len__(self) -> int:
        return len(first(self._channel_values.values()))

    def split(self, split_index: int):
        self._check_split_valid(split_index)

        if split_index == 0:
            return self.empty_like(self), self
        elif split_index == len(self):
            return self, self.empty_like(self)
        else:
            cls = type(self)
            splits = {
                label: pattern.split(split_index)
                for label, pattern in self.values.items()
            }
            left = {label: pattern[0] for label, pattern in splits.items()}
            right = {label: pattern[1] for label, pattern in splits.items()}
            return cls(left), cls(right)

    def flatten(self) -> Self:
        return self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({tuple(self.values)!r})"

    def __eq__(self, other):
        if not isinstance(other, ChannelPattern):
            return False
        return self.values == other.values

    def __getitem__(self, key):
        return self.values[key]


class Concatenate(SequencerInstruction):
    """A sequence of instructions to be executed consecutively.

    Attributes:
        instructions: The instructions to be executed
    """

    def __init__(
        self,
        instructions: Iterable[SequencerInstruction],
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
    def instructions(self) -> tuple[SequencerInstruction, ...]:
        return self._instructions

    def __len__(self) -> int:
        return self._len

    @cached_property
    def _len(self) -> int:
        return sum(len(instruction) for instruction in self.instructions)

    def split(self, split_index: int):
        self._check_split_valid(split_index)

        instruction_index = self._find_instruction_index(split_index)
        instruction_to_split = self.instructions[instruction_index]

        before_part, after_part = instruction_to_split.split(
            split_index - self._instruction_starts[instruction_index]
        )

        before_instruction = SequencerInstruction.join(
            self.instructions[:instruction_index] + (before_part,),
            channel_types=self.channel_types,
        )
        after_instruction = SequencerInstruction.join(
            (after_part,) + self.instructions[instruction_index + 1 :],
            channel_types=self.channel_types,
        )
        return before_instruction, after_instruction

    def _find_instruction_index(self, time: int) -> int:
        """Find the index of the instruction active at the given time index."""

        if time < 0:
            raise ValueError(f"Time index must be non-negative, got {time}.")
        if time >= len(self):
            raise ValueError(f"Time index must be less than {len(self)}, got {time}.")

        return int(np.searchsorted(self._instruction_starts, time, side="right") - 1)

    def flatten(self) -> SequencerPattern:
        """Return a flattened version of this instruction."""

        flattened = [instruction.flatten() for instruction in self.instructions]
        result = {}
        for label, dtype in self.channel_types.items():
            result[label] = ChannelPattern(
                np.concatenate(
                    [pattern[label].flatten().values for pattern in flattened]
                ),
                dtype=dtype,
            )
        return SequencerPattern(result)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.instructions!r})"

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
    def channel_types(self) -> dict[ChannelLabel, ChannelType]:
        return self.instructions[0].channel_types


class Repeat(SequencerInstruction):
    """Repeat a single instruction a given number of times.

    Attributes:
        instruction: The instruction to be repeated.
        number_repetitions: The number of times to repeat the instruction. Must be greater or equal to 2.
    """

    def __init__(
        self,
        instruction: SequencerInstruction,
        number_repetitions: int,
    ) -> None:
        self._instruction = instruction
        self._number_repetitions = number_repetitions
        if number_repetitions < 2:
            raise ValueError("Number of repetitions must be greater or equal to 2.")

    @property
    def instruction(self) -> SequencerInstruction:
        return self._instruction

    @property
    def number_repetitions(self) -> int:
        return self._number_repetitions

    def __len__(self) -> int:
        return self._len

    @cached_property
    def _len(self) -> int:
        return len(self.instruction) * self.number_repetitions

    def flatten(self) -> SequencerPattern:
        flattened = self.instruction.flatten()
        result = {}
        for label, dtype in self.channel_types.items():
            result[label] = ChannelPattern(
                np.tile(flattened[label].values, self.number_repetitions),
                dtype=dtype,
            )
        return SequencerPattern(result)

    def split(self, split_index: int):
        self._check_split_valid(split_index)
        instruction_length = len(self.instruction)

        before_part, after_part = self.instruction.split(
            split_index % instruction_length
        )

        before_repetitions = split_index // instruction_length
        before_block = self.instruction * before_repetitions
        before_instruction = SequencerInstruction.join(
            (before_block, before_part), channel_types=self.channel_types
        )

        after_repetitions = max(self.number_repetitions - before_repetitions - 1, 0)
        after_block = self.instruction * after_repetitions
        after_instruction = SequencerInstruction.join(
            (after_part, after_block), channel_types=self.channel_types
        )

        return before_instruction, after_instruction

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
    def channel_types(self) -> dict[ChannelLabel, ChannelType]:
        return self.instruction.channel_types


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))

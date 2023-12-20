import logging
import math
from abc import ABC, abstractmethod
from collections.abc import Mapping, Iterable
from functools import cached_property, singledispatchmethod, singledispatch
from typing import NewType, TypeVar, Any, Self

import numpy as np
from attr import define

from sequencer.channel import Concatenate as ChannelConcatenate, Repeat as ChannelRepeat
from sequencer.channel import Splittable, ChannelPattern
from sequencer.channel.channel_instructions import ChannelType, ChannelInstruction

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ChannelLabel = NewType("ChannelLabel", int)


@define(init=False, eq=False)
class SequencerInstructionOld(
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
    def __getitem__(self, key: ChannelLabel) -> ChannelInstruction:
        """Return the instruction for a single channel."""

        raise NotImplementedError

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

    def __add__(self, other) -> "SequencerInstructionOld":
        if isinstance(other, SequencerInstructionOld):
            return self.join([self, other], self.channel_types)
        else:
            raise TypeError(f"Can't concatenate {type(self)} and {type(other)}.")

    def __mul__(self, other: int) -> "SequencerInstructionOld":
        multiplier = int(other)
        if multiplier < 0:
            raise ValueError("Multiplier must be positive integer.")
        elif multiplier == 0:
            return self.empty_like(self)
        elif multiplier == 1:
            return self
        else:
            return RepeatOld(self, multiplier)

    def __rmul__(self, other) -> "SequencerInstructionOld":
        return self.__mul__(other)

    @classmethod
    def join(
        cls,
        instructions: Iterable["SequencerInstructionOld"],
        channel_types: Mapping[ChannelLabel, ChannelType],
    ) -> "SequencerInstructionOld":
        """Concatenate multiple instructions into a single instruction.

        This method removes empty instructions from the list and flattens nested concatenations.
        """

        instructions = [
            instruction for instruction in instructions if not instruction.is_empty()
        ]
        flattened_instructions: list[SequencerInstructionOld] = []
        for instruction in instructions:
            if isinstance(instruction, ConcatenateOld):
                flattened_instructions.extend(instruction.instructions)
            else:
                flattened_instructions.append(instruction)

        if len(flattened_instructions) == 0:
            return cls.empty(channel_types)
        elif len(flattened_instructions) == 1:
            return flattened_instructions[0]
        else:
            return ConcatenateOld(flattened_instructions)

    def is_empty(self) -> bool:
        return len(self) == 0

    @classmethod
    def empty(
        cls, channel_types: Mapping[ChannelLabel, ChannelType]
    ) -> "SequencerInstructionOld":
        """Return an empty instruction."""

        return SequencerPattern(
            {
                channel: ChannelPattern[Any].empty(dtype)
                for channel, dtype in channel_types.items()
            }
        )

    @classmethod
    def empty_like(cls, other: "SequencerInstructionOld") -> "SequencerInstructionOld":
        """Return an empty instruction with the same channel types as another instruction."""

        return cls.empty(other.channel_types)

    @abstractmethod
    def add_channel_instruction(
        self, channel: ChannelLabel, instruction: ChannelInstruction
    ) -> "SequencerInstructionOld":
        """Add an instruction for a single channel."""

        raise NotImplementedError

    def _check_can_add_channel(
        self, channel: ChannelLabel, instruction: ChannelInstruction
    ) -> None:
        if channel in self.channel_types:
            raise ValueError(f"Channel {channel} already exists.")
        elif len(instruction) != len(self):
            raise ValueError(
                f"Instruction for channel {channel} has wrong length. "
                f"Expected {len(self)}, got {len(instruction)}."
            )

    @classmethod
    def from_channel_instruction(
        cls, channel: ChannelLabel, instruction: ChannelInstruction
    ) -> "SequencerInstructionOld":
        """Return an instruction that only contains a single channel instruction."""

        return _from_channel_instruction(instruction, channel)

    @abstractmethod
    def get_last_values(self) -> dict[ChannelLabel, ChannelType]:
        """Return the last value of each channel."""

        raise NotImplementedError


@singledispatch
def _from_channel_instruction(
    instruction: ChannelInstruction, channel: ChannelLabel
) -> SequencerInstructionOld:
    """Return an instruction that only contains a single channel instruction."""

    raise NotImplementedError(f"Not implemented for {type(instruction)}.")


@_from_channel_instruction.register
def _(instruction: ChannelPattern, channel: ChannelLabel) -> SequencerInstructionOld:
    return SequencerPattern({channel: instruction})


@_from_channel_instruction.register
def _(
    instruction: ChannelConcatenate, channel: ChannelLabel
) -> SequencerInstructionOld:
    result = [
        _from_channel_instruction(channel_instruction, channel)
        for channel_instruction in instruction.instructions
    ]
    return SequencerInstructionOld.join(result, {channel: instruction.dtype})


@_from_channel_instruction.register
def _(instruction: ChannelRepeat, channel: ChannelLabel) -> SequencerInstructionOld:
    return RepeatOld(
        _from_channel_instruction(instruction.instruction, channel),
        instruction.number_repetitions,
    )


@define(init=False, eq=False)
class SequencerPattern(SequencerInstructionOld):
    """A sequence of output values for several channels."""

    _channel_values: dict[ChannelLabel, ChannelPattern]

    def __init__(self, channel_values: Mapping[ChannelLabel, ChannelPattern]) -> None:
        if not all(
            isinstance(values, ChannelPattern) for values in channel_values.values()
        ):
            raise TypeError("Channel values must be ChannelPattern instances.")
        if len(channel_values) == 0:
            raise ValueError("Pattern must contain at least one channel.")
        length = len(first(channel_values.values()))
        if not all(len(channel) == length for channel in channel_values.values()):
            raise ValueError("Channel patterns must have the same duration.")
        self._channel_values = dict(channel_values)

    def __hash__(self):
        key_hash = hash(tuple(self._channel_values.keys()))
        value_hash = hash(tuple(self._channel_values.values()))
        return hash((key_hash, value_hash))

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

    def __eq__(self, other):
        if not isinstance(other, SequencerPattern):
            return False
        return self._channel_values == other._channel_values

    def __getitem__(self, key):
        return self.values[key]

    def add_channel_instruction(
        self, channel: ChannelLabel, instruction: ChannelInstruction
    ) -> "SequencerInstructionOld":
        self._check_can_add_channel(channel, instruction)
        flattened = instruction.flatten()
        result = self.values
        result[channel] = flattened
        return type(self)(result)

    def get_first_values(self) -> dict[ChannelLabel, ChannelType]:
        """Return the first value of each channel."""

        return self.get_values_at(0)

    def get_last_values(self) -> dict[ChannelLabel, ChannelType]:
        """Return the last value of each channel."""

        return self.get_values_at(len(self) - 1)

    def get_values_at(self, index: int) -> dict[ChannelLabel, ChannelType]:
        """Return the value of each channel at a given index."""

        if self.is_empty():
            raise ValueError("Cannot get value of empty pattern.")

        # noinspection PyProtectedMember
        return {
            label: pattern._values[index]
            for label, pattern in self._channel_values.items()
        }


@define(init=False, eq=False)
class ConcatenateOld(SequencerInstructionOld):
    """A sequence of instructions to be executed consecutively.

    Attributes:
        instructions: The instructions to be executed
    """

    _instructions: tuple[SequencerInstructionOld, ...]
    _instruction_starts: np.ndarray

    def __init__(
        self,
        instructions: Iterable[SequencerInstructionOld],
    ) -> None:
        self._instructions = tuple(
            instruction for instruction in instructions if not instruction.is_empty()
        )
        self._instruction_starts = np.cumsum(
            [0] + [len(instruction) for instruction in instructions]
        )
        if len(self._instructions) <= 1:
            raise ValueError("Concatenation must have at least two instructions.")

    def __hash__(self):
        return hash(tuple(self._instructions))

    @property
    def instructions(self) -> tuple[SequencerInstructionOld, ...]:
        return self._instructions

    def __len__(self) -> int:
        return self._len

    def __getitem__(self, key: ChannelLabel) -> ChannelInstruction:
        return ChannelConcatenate(
            (instruction[key] for instruction in self.instructions)
        )

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

        before_instruction = SequencerInstructionOld.join(
            self.instructions[:instruction_index] + (before_part,),
            channel_types=self.channel_types,
        )
        after_instruction = SequencerInstructionOld.join(
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

    def __eq__(self, other):
        if not isinstance(other, ConcatenateOld):
            return False
        return self._instructions == other._instructions

    @cached_property
    def channel_types(self) -> dict[ChannelLabel, ChannelType]:
        return self.instructions[0].channel_types

    def add_channel_instruction(
        self, channel: ChannelLabel, channel_instruction: ChannelInstruction
    ) -> "SequencerInstructionOld":
        self._check_can_add_channel(channel, channel_instruction)

        result = []
        for instruction in self.instructions:
            left, right = channel_instruction.split(len(instruction))
            result.append(instruction.add_channel_instruction(channel, left))
            channel_instruction = right
        return self.join(result, channel_types=self.channel_types)

    def get_last_values(self) -> dict[ChannelLabel, ChannelType]:
        """Return the last value of each channel."""

        return self.instructions[-1].get_last_values()


@define(init=False, eq=False)
class RepeatOld(SequencerInstructionOld):
    """Repeat a single instruction a given number of times.

    Attributes:
        instruction: The instruction to be repeated.
        number_repetitions: The number of times to repeat the instruction. Must be greater or equal to 2.
    """

    _instruction: SequencerInstructionOld
    _number_repetitions: int

    def __init__(
        self,
        instruction: SequencerInstructionOld,
        number_repetitions: int,
    ) -> None:
        self._instruction = instruction
        self._number_repetitions = number_repetitions
        if number_repetitions < 2:
            raise ValueError("Number of repetitions must be greater or equal to 2.")

    def __hash__(self):
        return hash((self._instruction, self._number_repetitions))

    @property
    def instruction(self) -> SequencerInstructionOld:
        return self._instruction

    def __getitem__(self, item):
        return ChannelRepeat(self.instruction[item], self.number_repetitions)

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
        before_instruction = SequencerInstructionOld.join(
            (before_block, before_part), channel_types=self.channel_types
        )

        if split_index % instruction_length == 0:
            after_repetitions = self.number_repetitions - before_repetitions
            after_part = after_part * 0
        else:
            after_repetitions = max(self.number_repetitions - before_repetitions - 1, 0)

        after_block = self.instruction * after_repetitions
        after_instruction = SequencerInstructionOld.join(
            (after_part, after_block), channel_types=self.channel_types
        )

        return before_instruction, after_instruction

    def __eq__(self, other):
        if not isinstance(other, RepeatOld):
            return False
        return (
            self._instruction == other._instruction
            and self._number_repetitions == other._number_repetitions
        )

    def __mul__(self, other):
        multiplier = int(other) * self.number_repetitions
        if multiplier == 0:
            return self.empty_like(self)
        else:
            return RepeatOld(self.instruction, multiplier)

    @cached_property
    def channel_types(self) -> dict[ChannelLabel, ChannelType]:
        return self.instruction.channel_types

    def add_channel_instruction(
        self, channel: ChannelLabel, instruction_to_add: ChannelInstruction
    ) -> "SequencerInstructionOld":
        self._check_can_add_channel(channel, instruction_to_add)

        return self._add_channel_instruction(instruction_to_add, channel)

    @singledispatchmethod
    def _add_channel_instruction(
        self, instruction_to_add: ChannelInstruction, channel: ChannelLabel
    ) -> "SequencerInstructionOld":
        raise NotImplementedError

    @_add_channel_instruction.register
    def _(
        self, instruction_to_add: ChannelPattern, channel: ChannelLabel
    ) -> "SequencerInstructionOld":
        flattened = self.flatten()
        return flattened.add_channel_instruction(channel, instruction_to_add)

    @_add_channel_instruction.register
    def _(
        self, channel_instruction: ChannelConcatenate, channel: ChannelLabel
    ) -> "SequencerInstructionOld":
        instruction = self
        result = []
        for part in channel_instruction.instructions:
            left, instruction = instruction.split(len(part))
            result.append(left.add_channel_instruction(channel, part))
        return self.join(result, channel_types=self.channel_types)

    @_add_channel_instruction.register
    def _(
        self, instruction_to_add: ChannelRepeat, channel: ChannelLabel
    ) -> "SequencerInstructionOld":
        lcm = math.lcm(len(self.instruction), len(instruction_to_add.instruction))

        if lcm == len(self):
            return self.flatten().add_channel_instruction(channel, instruction_to_add)

        channel_macro_instruction = instruction_to_add.instruction * (
            lcm // len(instruction_to_add.instruction)
        )
        self_macro_instruction = self.instruction * (lcm // len(self.instruction))
        macro_instruction = self_macro_instruction.add_channel_instruction(
            channel, channel_macro_instruction
        )
        return RepeatOld(macro_instruction, len(self) // lcm)

    def get_last_values(self) -> dict[ChannelLabel, ChannelType]:
        """Return the last value of each channel."""

        return self.instruction.get_last_values()


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))


def to_flat_dict(
    instruction: SequencerInstructionOld,
) -> dict[ChannelLabel, np.ndarray]:
    """Return a dict containing the instruction for each channel."""

    flattened = instruction.flatten()
    return {label: pattern.values for label, pattern in flattened.values.items()}

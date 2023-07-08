from abc import ABC, abstractmethod
from typing import Self, Iterable, Mapping, NewType, TypeVar

import numpy as np

from .channel import ChannelPattern, ChannelInstruction
from .splittable import Splittable

ChannelLabel = NewType("ChannelLabel", int)


class SequencerInstruction(
    Splittable["SequencerInstruction"],
    ABC,
):
    """Base class to describe the output sequence of a several channels."""

    @abstractmethod
    def flatten(self) -> "SequencerPattern":
        """Flatten the instruction into a single pattern."""

        raise NotImplementedError

    @abstractmethod
    def set_channel_instruction(
        self, label: ChannelLabel, instruction: ChannelInstruction
    ) -> None:
        """Set the instruction for a single channel."""

        raise NotImplementedError

    @abstractmethod
    def number_channels(self) -> int:
        """Return the number of channels."""

        raise NotImplementedError


class SequencerPattern(SequencerInstruction):
    def __init__(self, channel_patterns: Mapping[ChannelLabel, ChannelPattern]) -> None:
        self.channel_patterns = dict(channel_patterns)

    @property
    def channel_patterns(self) -> dict[ChannelLabel, ChannelPattern]:
        return self._channel_patterns

    @channel_patterns.setter
    def channel_patterns(
        self, channel_patterns: Mapping[ChannelLabel, ChannelPattern]
    ) -> None:
        if len(channel_patterns) == 0:
            raise ValueError("Instruction must have at least one channel pattern.")
        duration = len(first(channel_patterns.values()))
        if not all(
            len(channel_pattern) == duration
            for channel_pattern in channel_patterns.values()
        ):
            raise ValueError("All channel patterns must have the same duration.")
        self._channel_patterns = dict(channel_patterns)
        self._check_length_valid()

    def __len__(self) -> int:
        return len(first(self.channel_patterns.values()))

    def split(self, split_index: int) -> tuple[Self, Self]:
        self._check_split_valid(split_index)

        splits = {
            name: channel_pattern.split(split_index)
            for name, channel_pattern in self.channel_patterns.items()
        }
        first_part = type(self)({name: split[0] for name, split in splits.items()})
        second_part = type(self)({name: split[1] for name, split in splits.items()})
        return first_part, second_part

    def number_channels(self) -> int:
        return len(self.channel_patterns)

    def flatten(self) -> Self:
        return self

    def set_channel_instruction(
        self, label: ChannelLabel, instruction: ChannelInstruction
    ) -> None:
        if self.number_channels() > 0:
            if len(instruction) != len(self):
                raise ValueError(
                    "Instruction must have the same duration as the existing"
                    " instruction."
                )
        self.channel_patterns[label] = instruction.flatten()


class Concatenate(SequencerInstruction):
    """A sequence of instructions to be executed consecutively.

    Attributes:
        instructions: The instructions to be executed
    """

    def __init__(
        self,
        instructions: Iterable[SequencerInstruction],
    ) -> None:
        self._instructions = tuple(instructions)
        self._instruction_starts = np.cumsum(
            [0] + [len(instruction) for instruction in instructions]
        )
        self._check_length_valid()

    @property
    def instructions(self) -> tuple[SequencerInstruction, ...]:
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


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))

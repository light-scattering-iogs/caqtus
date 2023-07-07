from abc import ABC
from typing import Self, Iterable

import numpy as np

from . import channel
from .splittable import Splittable


class Instruction(Splittable, ABC):
    pass


class Pattern(Instruction):
    def __init__(self, channel_patterns: Iterable[channel.Pattern]) -> None:
        self.channel_patterns = list(channel_patterns)

    @property
    def channel_patterns(self) -> list[channel.Pattern]:
        return self._channel_patterns

    @channel_patterns.setter
    def channel_patterns(self, channel_patterns: list[channel.Pattern]) -> None:
        if len(channel_patterns) == 0:
            raise ValueError("Instruction must have at least one channel pattern.")
        duration = len(channel_patterns[0])
        if not all(
            len(channel_pattern) == duration for channel_pattern in channel_patterns
        ):
            raise ValueError("All channel patterns must have the same duration.")
        self._channel_patterns = channel_patterns
        self._check_length_valid()

    def __len__(self) -> int:
        return len(self.channel_patterns[0])

    def split(self, split_index: int) -> tuple[Self, Self]:
        self._check_split_valid(split_index)

        splits = [
            channel_pattern.split(split_index)
            for channel_pattern in self.channel_patterns
        ]
        first_part = type(self)(split[0] for split in splits)
        second_part = type(self)(split[1] for split in splits)
        return first_part, second_part


class ConsecutiveInstructions(Instruction):
    def __init__(self, instructions: Iterable[Instruction]) -> None:
        self.instructions = list(instructions)

    @property
    def instructions(self) -> list[Instruction]:
        return self._instructions

    @instructions.setter
    def instructions(self, instructions: list[Instruction]):
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

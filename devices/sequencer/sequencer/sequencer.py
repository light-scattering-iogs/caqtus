from abc import ABC
from typing import Self, Iterable

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

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Self, Iterable, Mapping, NewType, TypeVar

from .channel import ChannelPattern, ChannelInstruction
from .splittable import Splittable

ChannelLabel = NewType("ChannelLabel", int)


class SequencerInstruction(
    Sequence[dict[ChannelLabel, ChannelPattern]],
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

    def __getitem__(self, item: int | slice):
        if isinstance(item, int):
            return {
                name: channel_pattern[item]
                for name, channel_pattern in self.channel_patterns.items()
            }
        elif isinstance(item, slice):
            indices = item.indices(len(self))
            return list(self[i] for i in indices)

        raise TypeError(f"Invalid argument type: {type(item)}")

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


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))

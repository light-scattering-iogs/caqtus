from typing import Self, Iterable, Mapping, NewType, TypeVar

from .channel import ChannelPattern
from .splittable import Splittable

ChannelLabel = NewType("ChannelLabel", int)


class SequencerPattern(Splittable["SequencerPattern"]):
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


_T = TypeVar("_T")


def first(iterable: Iterable[_T]) -> _T:
    return next(iter(iterable))

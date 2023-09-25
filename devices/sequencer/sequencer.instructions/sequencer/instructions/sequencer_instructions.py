from abc import ABC, abstractmethod
from typing import NewType, Iterator

import numpy as np
from attr import frozen, field

from .base_instructions import InternalPattern, Pattern, SequenceInstruction

ChannelLabel = NewType("ChannelLabel", int)
ChannelValue = NewType("ChannelValue", object)


@frozen
class SequencerInternalPattern(InternalPattern[dict[ChannelLabel, ChannelValue]]):
    values: dict[ChannelLabel, np.ndarray] = field()

    # noinspection PyUnresolvedReferences
    @values.validator
    def _validate_values(self, _, v):
        length = len(first(v.values()))
        for channel, array in v.items():
            if len(array) != length:
                raise ValueError(
                    f"Length of channel {channel} is {len(array)}, and it should be {length}"
                )

    def __len__(self):
        return len(first(self.values.values()))

    def __iter__(self) -> Iterator[dict[ChannelLabel, ChannelValue]]:
        for index in range(len(self)):
            yield {channel: array[index] for channel, array in self.values.items()}

    def __getitem__(self, item):
        if isinstance(item, int):
            return {channel: array[item] for channel, array in self.values.items()}
        elif isinstance(item, slice):
            return __class__(
                {channel: array[item] for channel, array in self.values.items()}
            )
        else:
            raise TypeError(f"Index must be int or slice, not {type(item)}")


class SequencerInstruction(SequenceInstruction[dict[ChannelLabel, ChannelValue]], ABC):
    @abstractmethod
    def flatten(self) -> "SequencerPattern":
        raise NotImplementedError()


@frozen
class SequencerPattern(Pattern[dict[ChannelLabel, ChannelValue]], SequencerInstruction):
    pattern: SequencerInternalPattern = field()

    def flatten(self) -> "SequencerPattern":
        return self


def first(iterable):
    return next(iter(iterable))

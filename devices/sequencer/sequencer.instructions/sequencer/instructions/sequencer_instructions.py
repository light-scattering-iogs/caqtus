from abc import ABC, abstractmethod
from typing import NewType, Iterator

import numpy as np
from attr import frozen, field

from .base_instructions import (
    InternalPattern,
    Pattern,
    SequenceInstruction,
    Add,
    Multiply,
)

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
    array: SequencerInternalPattern = field()

    def flatten(self) -> "SequencerPattern":
        return self


@frozen
class SequencerAdd(Add[dict[ChannelLabel, ChannelValue]], SequencerInstruction):
    left: SequencerInstruction
    right: SequencerInstruction

    def flatten(self) -> "SequencerPattern":
        left_pattern = self.left.flatten()
        right_pattern = self.right.flatten()

        if (
            not left_pattern.pattern.values.keys()
            == right_pattern.pattern.values.keys()
        ):
            raise ValueError("Left and right patterns must have the same channels")

        result = {}
        for channel in left_pattern.pattern.values.keys():
            result[channel] = np.concatenate(
                (
                    left_pattern.pattern.values[channel],
                    right_pattern.pattern.values[channel],
                )
            )
        return SequencerPattern(SequencerInternalPattern(result))


@frozen
class SequencerMultiply(
    Multiply[dict[ChannelLabel, ChannelValue]], SequencerInstruction
):
    repetitions: int
    instruction: SequencerInstruction

    def flatten(self) -> "SequencerPattern":
        pattern = self.instruction.flatten().pattern
        result = {}
        for channel in pattern.values.keys():
            result[channel] = np.tile(pattern.values[channel], self.repetitions)
        return SequencerPattern(SequencerInternalPattern(result))


def first(iterable):
    return next(iter(iterable))

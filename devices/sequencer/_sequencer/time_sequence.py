from collections.abc import Iterable
from numbers import Real

import numpy as np

from .channel_config import ChannelConfig
from .time_sequence_instructions import (
    Instruction,
    Pattern,
)


class TimeSequence:
    """Represents a sequence of values for a set of channels over time.

    This class represents a 2D table of values for a set of channels over time. The table is indexed by time and channel
    index. The time axis is discrete and has a fixed time step. Each channel has a fixed numpy dtype.
    """

    def __init__(self, channel_configs: Iterable[ChannelConfig]):
        """Create a new empty time sequence."""

        self._steps: list[Instruction] = []
        self._channel_configs = tuple(channel_configs)

    @property
    def channel_configs(self) -> tuple[ChannelConfig, ...]:
        """The configuration of the channels in the time sequence."""

        return self._channel_configs

    @property
    def number_channels(self) -> int:
        """The number of channels in the time sequence."""

        return len(self._channel_configs)

    def total_duration(self) -> int:
        """The total number of ticks in the time sequence."""

        return sum(step.total_duration() for step in self._steps)

    def unroll(self) -> Pattern:
        """Unroll the time sequence into a single pattern.

        This function evaluates all instructions and concatenates them into explicit steps. It will replace loops by
        their unrolled content. Note that this may result in a very large number of steps.
        """

        return Pattern.concatenate(*(step.unroll() for step in self._steps))

    def apply(self, channel_index: int, fun: np.ufunc, *args, **kwargs):
        """Apply a function to the values of a channel in the time sequence."""

        if channel_index >= self.number_channels:
            raise ValueError(
                f"Channel index {channel_index} out of range for time sequence with "
                f"{self.number_channels} channels"
            )
        for step in self._steps:
            step.apply(channel_index, fun, *args, **kwargs)

    def append(self, instruction: Instruction):
        """Append an instruction to the time sequence."""

        self._steps.append(instruction)

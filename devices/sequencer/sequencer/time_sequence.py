from collections.abc import Iterable
from functools import singledispatchmethod
from numbers import Real, Integral

import numpy as np

from .channel_config import ChannelConfig
from .time_sequence_instructions import (
    Instruction,
    Pattern,
    InstructionNotSupportedError,
)


class TimeSequence:
    """Represents a sequence of values for a set of channels over time.

    This class represents a 2D table of values for a set of channels over time. The table is indexed by time and channel
    index. The time axis is discrete and has a fixed time step. Each channel has a fixed numpy dtype.
    """

    def __init__(self, time_step: Real, channel_configs: Iterable[ChannelConfig]):
        """Create a new empty time sequence."""

        self._time_step = float(time_step)
        self._steps: list[Instruction] = []
        self._channel_configs = tuple(channel_configs)

    @property
    def time_step(self) -> float:
        """The duration in seconds of a single time tick."""

        return self._time_step

    @property
    def channel_configs(self) -> tuple[ChannelConfig, ...]:
        """The configuration of the channels in the time sequence."""

        return self._channel_configs

    @property
    def number_channels(self) -> int:
        """The number of channels in the time sequence."""

        return len(self._channel_configs)

    def append_new_pattern(self, durations: Iterable[Integral]) -> Pattern:
        """Create a new pattern with the given durations.

        The pattern created contains default values for all channels. It is automatically added at the end of the
        sequence. The pattern is returned so that it can be modified.
        """

        durations = np.array(durations, dtype=np.uint)
        channel_values = [
            np.full(len(durations), config.default_value, config.dtype)
            for config in self._channel_configs
        ]
        pattern = Pattern(durations, channel_values)
        self._append_instruction(pattern)
        return pattern

    def total_duration(self) -> int:
        """The total number of ticks in the time sequence."""

        return sum(step.total_duration() for step in self._steps)

    def unroll(self) -> Pattern:
        """Unroll the time sequence into a single pattern.

        This function evaluates all instructions and concatenates them into explicit steps. It will replace loops by
        their unrolled content. Note that this may result in a very large number of steps.
        """

        if not all(isinstance(step, Pattern) for step in self._steps):
            raise InstructionNotSupportedError("Cannot unroll non-pattern instructions")
        return Pattern.concatenate(*self._steps)  # type: ignore

    def apply(self, channel_index: int, fun: np.ufunc, *args, **kwargs):
        """Apply a function to the values of a channel in the time sequence."""

        if channel_index >= self.number_channels:
            raise ValueError(
                f"Channel index {channel_index} out of range for time sequence with "
                f"{self.number_channels} channels"
            )
        for step in self._steps:
            step.apply(channel_index, fun, *args, **kwargs)

    @singledispatchmethod
    def _append_instruction(self, instruction: Instruction):
        """Append an instruction to the time sequence."""

        raise InstructionNotSupportedError(
            f"Instruction of type {type(instruction)} not supported"
        )

    @_append_instruction.register
    def _(self, instruction: Pattern):
        self._steps.append(instruction)

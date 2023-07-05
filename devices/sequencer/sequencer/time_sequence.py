from functools import singledispatchmethod
from numbers import Real
from typing import Optional

import numpy as np

from .time_sequence_instructions import Instruction, Pattern, InstructionNotSupportedError


class TimeSequence:
    """Represents a sequence of values for a set of channels over time.

    This class represents a 2D table of values for a set of channels over time. The table is indexed by time and channel
    index. The time axis is discrete and has a fixed time step. Each channel has a fixed numpy dtype.

    Attributes:
    """

    def __init__(self, time_step: Real):
        """Create a new empty time sequence."""

        self._time_step = float(time_step)
        self._steps: list[Instruction] = []
        self._channel_dtypes: Optional[tuple[np.dtype, ...]] = None

    @property
    def time_step(self) -> float:
        """The duration in seconds of a single time tick."""

        return self._time_step

    @property
    def channel_dtypes(self) -> Optional[tuple[np.dtype, ...]]:
        """The dtypes of the channels in the time sequence.

        This is None if the time sequence is empty, which is different from an empty tuple if the time sequence has
        no channels.
        """

        return self._channel_dtypes

    def total_duration(self) -> int:
        """The total number of ticks in the time sequence."""

        return sum(step.total_duration() for step in self._steps)

    def unroll(self) -> Pattern:
        """Unroll the time sequence into a single step.

        This function evaluates all instructions and concatenates them into explicit steps. It will replace loops by
        their unrolled content. Note that this may result in a very large number of steps.
        """

        if not all(isinstance(step, Pattern) for step in self._steps):
            raise InstructionNotSupportedError("Cannot unroll non-pattern instructions")
        return Pattern.concatenate(*self._steps)  # type: ignore

    @singledispatchmethod
    def append_instruction(self, instruction: Instruction):
        """Append an instruction to the time sequence."""

        raise InstructionNotSupportedError(
            f"Instruction of type {type(instruction)} not supported"
        )

    @append_instruction.register
    def _(self, instruction: Pattern):
        if self._channel_dtypes is None:
            self._channel_dtypes = instruction.channel_dtypes
        elif self._channel_dtypes != instruction.channel_dtypes:
            raise ValueError(
                f"Can only append steps with channel dtypes {self._channel_dtypes}, but"
                f" got {instruction.channel_dtypes}"
            )

        if self._steps and isinstance(last_step := self._steps[-1], Pattern):
            # noinspection PyTypeChecker
            self._steps[-1] = Pattern.concatenate(last_step, instruction)
        else:
            self._steps.append(instruction)

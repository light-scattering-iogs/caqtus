from functools import singledispatchmethod
from numbers import Real
from typing import Optional

from numpy.typing import DTypeLike

from .channel_name import ChannelName
from .time_sequence_instructions import Instruction, Steps


class TimeSequence:
    """Represents a sequence of values for a set of channels over time.

    The sequence is represented as a list of instructions.

    """

    def __init__(self, time_step: Real):
        """Create a new empty time sequence.

        Args:
            time_step: The duration in seconds that represents 1 duration unit.

        """
        self._time_step = float(time_step)
        self._steps: list[Instruction] = []
        self._channel_dtypes: Optional[dict[ChannelName, DTypeLike]] = None

    @property
    def time_step(self) -> float:
        return self._time_step

    @property
    def channel_dtypes(self) -> dict[ChannelName, DTypeLike]:
        """The dtypes of the channels in the time sequence."""

        if self._channel_dtypes is None:
            return {}
        return dict(self._channel_dtypes)

    def duration(self) -> int:
        """The duration of the time sequence in units of time_step."""

        return sum(step.duration() for step in self._steps)

    def unroll(self) -> Steps:
        """Unroll the time sequence into a single step.

        This function evaluates all instructions and concatenates them into explicit steps. It will replace loops by
        their unrolled content. Note that this may result in a very large number of steps.
        """

        if not all(isinstance(step, Steps) for step in self._steps):
            raise NotImplementedError("Cannot unroll non-step instructions")
        return Steps.concatenate(*self._steps)

    @singledispatchmethod
    def append_instruction(self, instruction: Instruction):
        """Append an instruction to the time sequence."""

        raise NotImplementedError(
            f"Instruction of type {type(instruction)} not supported"
        )

    @append_instruction.register
    def _(self, instruction: Steps):
        if self._channel_dtypes is None:
            self._channel_dtypes = instruction.channel_dtypes
        elif self._channel_dtypes != instruction.channel_dtypes:
            raise ValueError("Inconsistent channel dtypes")

        if self._steps and isinstance(last_step := self._steps[-1], Steps):
            # noinspection PyTypeChecker
            self._steps[-1] = Steps.concatenate(last_step, instruction)
        else:
            self._steps.append(instruction)

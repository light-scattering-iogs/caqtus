from abc import ABC, abstractmethod
from numbers import Integral
from typing import Self, Iterable

import numpy as np
from numpy.typing import ArrayLike


class Instruction(ABC):
    """Base class for instructions in a time sequence."""

    @abstractmethod
    def total_duration(self) -> int:
        """The total duration of the instruction in units of time_step."""

        raise NotImplementedError

    @abstractmethod
    def apply(self, channel_index: int, fun: np.ufunc, *args, **kwargs):
        """Apply a function to the values of a channel in the instruction.

        The result will be stored in place.
        """

        raise NotImplementedError


class Pattern(Instruction):
    """Dense 2D table of values for a set of channels over time."""

    def __init__(self, durations: ArrayLike, channel_values: Iterable[np.ndarray]):
        self._durations = np.array(durations, dtype=np.uint)
        self._channel_values = tuple(values for values in channel_values)

    @property
    def durations(self) -> np.ndarray[np.uint]:
        return self._durations

    def set_values(self, channel_index: int, values: ArrayLike):
        """Set the values of a channel in the pattern."""

        array = np.array(values, dtype=self._channel_values[channel_index].dtype)
        if array.ndim != 1:
            raise ValueError(f"Channel values must be 1D")
        if len(array) != len(self._durations):
            raise ValueError(
                f"Expected {len(self._durations)} values, but got {len(array)}"
            )
        self._channel_values[channel_index][:] = array

    @property
    def number_channels(self) -> int:
        return len(self._channel_values)

    @property
    def channel_values(self) -> tuple[np.ndarray, ...]:
        return self._channel_values

    def total_duration(self) -> int:
        return self._durations.sum()

    def apply(self, channel_index: int, fun: np.ufunc, *args, **kwargs):
        if channel_index >= self.number_channels:
            raise ValueError(f"Invalid channel index {channel_index}")

        result = fun(self._channel_values[channel_index], *args, **kwargs)
        result = np.array(result, dtype=self._channel_values[channel_index].dtype)

        if result.shape != self._channel_values[channel_index].shape:
            raise ValueError(
                f"Function result has shape {result.shape}, but expected"
                f" {self._channel_values[channel_index].shape}"
            )
        self._channel_values[channel_index][:] = result

    # noinspection PyProtectedMember
    @classmethod
    def concatenate(cls, *steps: Self) -> Self:
        """Concatenate multiple steps along their time axis into a new single pattern.

        Args:
            steps: The steps to concatenate. Must have the same number of channels and the same channel dtypes.
        """

        durations = np.concatenate([s._durations for s in steps])

        if not steps:
            raise ValueError(f"Must provide at least one step to concatenate")

        concatenated_channel_values = []

        for channel_index in range(steps[0].number_channels):
            concatenated_values = np.concatenate(
                [s.channel_values[channel_index] for s in steps]
            )
            concatenated_channel_values.append(concatenated_values)

        result = cls(durations, concatenated_channel_values)
        return result


class Repeat(Instruction):
    """Repeat other instructions a number of times."""

    def __init__(
        self, instructions: Iterable[Instruction], number_repetitions: Integral
    ):
        self._instruction = list(instructions)
        if number_repetitions < 0:
            raise ValueError(f"Number of repetitions must be positive")
        self._number_repeats = int(number_repetitions)

    def total_duration(self) -> int:
        return sum(i.total_duration() for i in self._instruction) * self._number_repeats

    def apply(self, channel_index: int, fun: np.ufunc, *args, **kwargs):
        for instruction in self._instruction:
            instruction.apply(channel_index, fun, *args, **kwargs)


class InstructionNotSupportedError(NotImplementedError):
    pass

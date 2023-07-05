from abc import ABC, abstractmethod
from numbers import Integral
from typing import Optional, Self, Iterable

import numpy as np
from numpy.typing import ArrayLike, DTypeLike


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

    def __init__(self, durations: ArrayLike):
        self._durations = np.array(durations, dtype=np.uint)
        self._channel_dtypes = tuple[np.dtype, ...]()
        self._channel_values = tuple[np.ndarray, ...]()

    def append_channel(
        self,
        values: ArrayLike,
        dtype: Optional[DTypeLike] = None,
    ):
        """Append a new channel to the pattern."""

        array = np.array(values, dtype=dtype)
        if array.ndim != 1:
            raise ValueError(f"Channel values must be 1D")
        if len(array) != len(self._durations):
            raise ValueError(
                f"Expected {len(self._durations)} values, but got {len(array)}"
            )
        self._channel_values = self._channel_values + (array,)

    @property
    def channel_dtypes(self) -> tuple[np.dtype, ...]:
        return tuple(values.dtype for values in self._channel_values)

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
        channel_values = list(self._channel_values)
        channel_values[channel_index] = result
        self._channel_values = tuple(channel_values)

    # noinspection PyProtectedMember
    @classmethod
    def concatenate(cls, *steps: Self) -> Self:
        """Concatenate multiple steps along their time axis into a new single pattern.

        Args:
            steps: The steps to concatenate. Must have the same number of channels and the same channel dtypes.
        """

        durations = np.concatenate([s._durations for s in steps])
        result = cls(durations)

        if not steps:
            return result

        for channel_index, channel_dtype in enumerate(steps[0].channel_dtypes):
            if any(s.channel_dtypes[channel_index] != channel_dtype for s in steps):
                raise ValueError(
                    f"Incompatible dtypes when concatenating channel {channel_index}"
                )
            concatenated_values = np.concatenate(
                [s._channel_values[channel_index] for s in steps]
            )
            result.append_channel(concatenated_values, dtype=channel_dtype)
        return result


class Repeat(Instruction):
    """Repeat other instructions a number of times."""

    def __init__(self, instructions: Iterable[Instruction], number_repetitions: Integral):
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

from abc import ABC, abstractmethod
from typing import Optional, Self

import numpy as np
from numpy.typing import ArrayLike, DTypeLike

from .channel_name import ChannelName


class Instruction(ABC):
    """Base class for instructions in a time sequence."""

    @abstractmethod
    def duration(self) -> int:
        """The duration of the instruction in units of time_step."""

        raise NotImplementedError


class Steps(Instruction):
    def __init__(self, durations: ArrayLike):
        self._durations = np.array(durations, dtype=np.uint)
        self._channel_dtypes: dict[ChannelName, DTypeLike] = {}
        self._channel_values: dict[ChannelName, np.ndarray] = {}

    def add_channel_values(
        self,
        channel_name: ChannelName,
        values: ArrayLike,
        dtype: Optional[DTypeLike] = None,
    ):
        self._channel_values[channel_name] = np.array(values, dtype=dtype)
        self._channel_dtypes[channel_name] = self._channel_values[channel_name].dtype

    @property
    def channel_dtypes(self) -> dict[ChannelName, DTypeLike]:
        return dict(self._channel_dtypes)

    def duration(self) -> int:
        return self._durations.sum()

    @classmethod
    def concatenate(cls, *steps: Self) -> Self:
        """Concatenate multiple steps into a single step along their time axis.

        Args:
            steps: The steps to concatenate. Must have the same channels and dtypes.
        """

        durations = np.concatenate([s._durations for s in steps])
        result = cls(durations)
        for channel_name in steps[0]._channel_values:
            expected_dtype = steps[0]._channel_values[channel_name].dtype
            if any(
                s._channel_values[channel_name].dtype != expected_dtype for s in steps
            ):
                raise ValueError(
                    f"Channel {channel_name} does not have the same dtype in all steps"
                )
            concatenated_values = np.concatenate(
                [s._channel_values[channel_name] for s in steps]
            )
            result.add_channel_values(channel_name, concatenated_values)
        return result

from abc import ABC
from numbers import Real
from typing import NewType, Optional

import numpy as np
from numpy.typing import ArrayLike, DTypeLike

ChannelName = NewType("ChannelName", str)


class TimeSequence:
    """ """

    def __init__(self, time_step: Real):
        self._time_step = float(time_step)
        self._steps: list[TimeSequence.Instruction] = []
        self._channel_dtypes: Optional[dict[ChannelName, DTypeLike]] = None

    @property
    def time_step(self) -> float:
        return self._time_step

    def add_steps(self, steps: "TimeSequence.Steps"):
        if steps._channel_dtypes is None:
            raise ValueError("Steps must have channel values")



    class Instruction(ABC):
        pass

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

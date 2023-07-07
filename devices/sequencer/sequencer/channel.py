from typing import TypeVar, Generic, Any, Self, Iterable

import numpy as np
from numpy.typing import DTypeLike

from .splittable import Splittable

ChannelType = TypeVar("ChannelType", bound=DTypeLike)


class Pattern(Splittable["Pattern[ChannelType]"], Generic[ChannelType]):
    """A sequence of values to be output on a channel."""

    def __init__(self, values: Iterable[ChannelType]) -> None:
        self.values = np.array(values)

    @property
    def values(self) -> np.ndarray[Any, ChannelType]:
        return self._values

    @values.setter
    def values(self, values: np.ndarray[Any, ChannelType]) -> None:
        self._values = values
        self._check_length_valid()

    def __len__(self) -> int:
        return len(self.values)

    def split(self, split_index: int) -> tuple[Self, Self]:
        self._check_split_valid(split_index)
        cls = type(self)
        return cls(self.values[:split_index]), cls(self.values[split_index:])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.values!r})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.values!s})"

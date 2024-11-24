from collections.abc import Sized
from typing import Protocol

import numpy as np
from typing_extensions import TypeVar

DataT_co = TypeVar("DataT_co", covariant=True, bound=np.generic, default=np.generic)


class SubInstruction(Sized, Protocol):
    pass


class HasDType[DataT: np.generic](SubInstruction, Protocol):
    def dtype(self) -> np.dtype[DataT]: ...


SubInstrT = TypeVar(
    "SubInstrT", bound=SubInstruction, covariant=True, default=SubInstruction
)


class Addable[T, R](SubInstruction, Protocol):
    def __add__(self, other: T) -> R: ...

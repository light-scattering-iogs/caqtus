from collections.abc import Sized
from typing import Protocol

import numpy as np
from typing_extensions import TypeVar

DataT = TypeVar("DataT", np.bool, np.int64, np.float64, np.void)


class SubInstruction(Sized, Protocol):
    def dtype(self) -> np.dtype: ...


class HasDType[DataT: np.generic](SubInstruction, Protocol):
    def dtype(self) -> np.dtype[DataT]: ...


SubInstrT = TypeVar(
    "SubInstrT", bound=SubInstruction, covariant=True, default=SubInstruction
)

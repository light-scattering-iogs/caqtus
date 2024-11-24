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

T = TypeVar("T", contravariant=True, bound=SubInstruction, default=SubInstruction)
R = TypeVar("R", covariant=True, bound=SubInstruction, default=SubInstruction)

InstrT_co = TypeVar(
    "InstrT_co", bound=SubInstruction, covariant=True, default=SubInstruction
)
InstrT_contra = TypeVar(
    "InstrT_contra", bound=SubInstruction, contravariant=True, default=SubInstruction
)
InstrT_inv = TypeVar(
    "InstrT_inv",
    bound=SubInstruction,
    contravariant=False,
    covariant=False,
    default=SubInstruction,
)


class Addable(SubInstruction, Protocol[InstrT_contra, InstrT_co]):
    def __add__(self, other: InstrT_contra) -> InstrT_co: ...


class Multipliable(SubInstruction, Protocol[InstrT_co]):
    def __mul__(self, other: int) -> InstrT_co: ...

    def __rmul__(self, other: int) -> InstrT_co: ...

from typing import Protocol, TypeVar

import numpy as np

from ._typing import SubInstruction


def _normalize_index(index: int, length: int) -> int:
    normalized = index if index >= 0 else length + index
    if not 0 <= normalized < length:
        raise IndexError(f"Index {index} is out of bounds for length {length}")
    return normalized


def _normalize_slice_index(index: int, length: int) -> int:
    normalized = index if index >= 0 else length + index
    if not 0 <= normalized <= length:
        raise IndexError(f"Slice index {index} is out of bounds for length {length}")
    return normalized


def _normalize_slice(slice_: slice, length: int) -> tuple[int, int, int]:
    step = slice_.step or 1
    if step == 0:
        raise ValueError("Slice step cannot be zero")
    if slice_.start is None:
        start = 0 if step > 0 else length - 1
    else:
        start = _normalize_slice_index(slice_.start, length)
    if slice_.stop is None:
        stop = length if step > 0 else -1
    else:
        stop = _normalize_slice_index(slice_.stop, length)

    return start, stop, step


class Indexable[DataT: np.generic](SubInstruction, Protocol):
    def __getitem__(self, item: int, /) -> DataT: ...


SliceT_contra = TypeVar(
    "SliceT_contra", bound=SubInstruction, contravariant=True, default=SubInstruction
)
SliceT_co = TypeVar(
    "SliceT_co", bound=SubInstruction, covariant=True, default=SubInstruction
)


SliceT = TypeVar("SliceT", bound=SubInstruction, covariant=True, default=SubInstruction)


class SupportsSlicing(SubInstruction, Protocol[SliceT]):
    def __getitem__(self, item: slice, /) -> SliceT: ...

from typing import Generic

import numpy as np
from numpy.typing import NDArray

from ._typing import DataT


class Pattern(Generic[DataT]):
    def __init__(self, values: NDArray[DataT]):
        assert isinstance(values, np.ndarray)
        assert values.ndim == 1
        assert len(values) > 0
        self._array = values

    @property
    def values(self) -> NDArray[DataT]:
        return self._array

    def dtype(self) -> np.dtype[DataT]:
        return self._array.dtype

    def __repr__(self) -> str:
        return f"Pattern({self._array!r})"

    def __str__(self) -> str:
        return str(self._array)

    def __len__(self) -> int:
        return len(self._array)

    def __getitem__(self, index: int) -> DataT:
        return self._array[index]

from typing import NewType

import numpy as np

type FloatArray[Shape: tuple[int, ...]] = np.ndarray[Shape, np.dtype[np.floating]]
type FloatArray1D[Length: int] = FloatArray[tuple[Length]]

SortedFloatArray = NewType("SortedFloatArray", FloatArray1D)

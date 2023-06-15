from numbers import Real
from typing import TypeVar

import numpy as np

Width = TypeVar("Width", bound=int)
Height = TypeVar("Height", bound=int)

T = TypeVar("T", bound=Real)

Image = np.ndarray[tuple[Width, Height], np.dtype[T]]

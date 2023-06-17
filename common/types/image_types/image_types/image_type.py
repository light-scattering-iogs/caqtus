from numbers import Real
from typing import TypeVar, NewType

import numpy as np

from data_types import DataLabel

Width = TypeVar("Width", bound=int)
Height = TypeVar("Height", bound=int)

T = TypeVar("T", bound=Real)

Image = np.ndarray[tuple[Width, Height], np.dtype[T]]

ImageLabel = NewType("ImageLabel", DataLabel)

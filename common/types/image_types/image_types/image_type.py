from numbers import Real
from typing import TypeVar

from numpy.typing import NDArray

Width = TypeVar("Width", bound=int)
Height = TypeVar("Height", bound=int)

Image = NDArray[tuple[Width, Height], Real]

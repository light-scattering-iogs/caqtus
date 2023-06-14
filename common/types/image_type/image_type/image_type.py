from numbers import Real
from typing import TypeVar

from numpy.typing import NDArray

Width = TypeVar("Width")
Height = TypeVar("Height")

Image = NDArray[tuple[Width, Height], Real]

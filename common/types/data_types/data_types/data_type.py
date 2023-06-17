from numbers import Real
from typing import TypeAlias

import numpy as np

from image_type import Image

Array = np.ndarray
Data: TypeAlias = (
    bool | str | Real | Array | Image | dict[str, "Data"] | list["Data"] | tuple["Data"]
)

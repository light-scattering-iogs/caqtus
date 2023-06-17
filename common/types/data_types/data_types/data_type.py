from numbers import Real
from typing import TypeAlias

import numpy as np


Array = np.ndarray
Data: TypeAlias = (
    bool | str | Real | Array | dict[str, "Data"] | list["Data"] | tuple["Data"]
)

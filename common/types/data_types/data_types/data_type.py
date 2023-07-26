from numbers import Real
from typing import TypeAlias

import numpy as np

DataKey: TypeAlias = bool | str | Real | tuple["DataKey", ...]


Array = np.ndarray
Data: TypeAlias = (
        bool | str | Real | Array | dict[DataKey, "Data"] | list["Data"] | tuple["Data"]
)

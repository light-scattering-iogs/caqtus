from typing import TypeAlias

import numpy as np

Array = np.ndarray
StructuredData: TypeAlias = (
    dict[str, "StructuredData"]
    | list["StructuredData"]
    | float
    | int
    | str
    | bool
    | None
)

Data: TypeAlias = StructuredData | Array

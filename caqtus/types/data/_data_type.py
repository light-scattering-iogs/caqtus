from __future__ import annotations

from typing import TypeAlias

import numpy as np

#: A type alias for numpy arrays.
type Array = np.ndarray


StructuredData: TypeAlias = (
    dict[str, "StructuredData"]
    | list["StructuredData"]
    | float
    | int
    | str
    | bool
    | None
)
"""A recursive union of basic types.

It can be used to represent complex data, possibly nested.
"""

type Data = Array | StructuredData
"""A sum type of structured data and arrays.

Only objects that are instances of this type can be saved for a shot.

Note that it is not possible to have structured data containing arrays.
"""

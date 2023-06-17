from numbers import Real
from typing import TypeGuard, Any

from image_type import Image
from .data_type import Data, Array


def is_data(data: Any) -> TypeGuard[Data]:
    """Check if data has a valid data type.

    Only data with the following types are considered valid:
    - bool
    - str
    - Real
    - np.ndarray
    - Image
    - dict[str, Data]
    - list[Data]
    - tuple[Data]
    """

    if isinstance(data, bool | str | Real | Array | Image):
        return True
    elif isinstance(data, (list, tuple)):
        return all(is_data(x) for x in data)
    elif isinstance(data, dict):
        return all(isinstance(k, str) and is_data(v) for k, v in data.items())

    return False

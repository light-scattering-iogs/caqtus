from numbers import Real
from typing import TypeGuard, Any

from .data_type import Data, Array, DataKey


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

    if isinstance(data, bool | str | Real | Array):
        return True
    elif isinstance(data, (list, tuple)):
        return all(is_data(x) for x in data)
    elif isinstance(data, dict):
        return all(is_valid_key(k) and is_data(v) for k, v in data.items())

    return False


def is_valid_key(value: Any) -> TypeGuard[DataKey]:
    if isinstance(value, bool | str | Real):
        return True
    elif isinstance(value, tuple):
        return all(is_valid_key(x) for x in value)

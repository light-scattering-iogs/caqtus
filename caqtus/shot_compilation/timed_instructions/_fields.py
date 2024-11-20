from typing import Any

import numpy as np
from typing_extensions import TypeIs


def get_field[
    S
](array: np.ndarray[S, np.dtype[np.void]], field: str) -> np.ndarray[
    S, np.dtype[np.generic]
]:
    """Get a field from a structured array.

    Args:
        array: The structured array.
        field: The name of the field to get.

    Returns:
        The field as a regular array.
    """

    return array[field]


def has_dtype[
    T: np.generic
](array: np.ndarray, dtype: type[T]) -> TypeIs[np.ndarray[Any, np.dtype[T]]]:
    """Check if an array has a given dtype.

    Args:
        array: The array to check.
        dtype: The dtype to check for.

    Returns:
        True if the array has the given dtype.
    """

    return array.dtype == dtype

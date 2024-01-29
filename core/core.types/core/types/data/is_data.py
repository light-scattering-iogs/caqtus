from typing import TypeGuard, Any

import numpy as np

from .data_type import Data


def is_data(data: Any) -> TypeGuard[Data]:
    """Check if data has a valid data type."""

    if isinstance(data, (bool, int, str, float, np.ndarray)):
        return True
    elif isinstance(data, (list, tuple)):
        return all(is_data(x) for x in data)
    elif isinstance(data, dict):
        return all(isinstance(k, str) and is_data(v) for k, v in data.items())

    return False

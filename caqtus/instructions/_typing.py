import numpy as np
from typing_extensions import TypeVar

DataT = TypeVar("DataT", covariant=True, bound=np.generic, default=np.generic)

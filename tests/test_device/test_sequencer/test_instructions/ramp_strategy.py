import numpy as np
from hypothesis.strategies import SearchStrategy, integers, floats, builds

from caqtus.shot_compilation.timed_instructions import Ramp


def ramp_strategy() -> SearchStrategy[Ramp]:
    return builds(
        Ramp._create,
        start=floats(
            allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6
        ).map(np.float64),
        stop=floats(
            allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6
        ).map(np.float64),
        length=integers(min_value=1, max_value=1000),
    )

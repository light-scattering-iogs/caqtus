import numpy as np
from hypothesis.extra.numpy import arrays, from_dtype
from hypothesis.strategies import integers, SearchStrategy

from caqtus.shot_compilation.timed_instructions import Pattern, InstrType


def generate_pattern(length: int, offset: int = 0) -> Pattern[np.int64]:
    return Pattern(np.arange(offset, offset + length))


def pattern(
    dtype: InstrType, min_length: int = 0, max_length=1000
) -> SearchStrategy[Pattern[InstrType]]:
    return arrays(
        dtype=dtype,
        shape=integers(min_value=min_length, max_value=max_length),
        elements=from_dtype(np.dtype(dtype), allow_infinity=False, allow_nan=False),
    ).map(Pattern)

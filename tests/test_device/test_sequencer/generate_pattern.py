import numpy as np

from caqtus.device.sequencer.instructions import Pattern
from hypothesis.extra.numpy import arrays
from hypothesis.strategies import composite, integers


def generate_pattern(length: int, offset: int = 0) -> Pattern:
    return Pattern(np.arange(offset, offset + length))


@composite
def bool_pattern(draw, length=integers(min_value=1, max_value=1000)) -> Pattern[bool]:
    a = draw(arrays(dtype=np.bool_, shape=(draw(length),)))
    return Pattern(a)

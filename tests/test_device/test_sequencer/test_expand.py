from hypothesis import given
from hypothesis.strategies import integers

from .generate_pattern import bool_pattern
from caqtus.device.sequencer.compilation.expand import expand_left


@given(bool_pattern(), integers(min_value=0))
def test(pattern, n):
    expanded, excess = expand_left(pattern, n)
    assert len(expanded) == len(pattern)
    for i in range(len(expanded)):
        assert expanded.array[i] == any(pattern.array[i : i + n + 1])

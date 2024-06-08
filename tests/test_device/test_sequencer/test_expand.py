import numpy as np
from hypothesis import given
from hypothesis.strategies import integers

from .generate_pattern import bool_pattern
from .generate_concatenate import bool_concatenation
from caqtus.device.sequencer.compilation.expand import expand_left


@given(bool_pattern(), integers(min_value=0))
def test_pattern(pattern, n):
    expanded, excess = expand_left(pattern, n)
    assert len(expanded) == len(pattern)
    for i in range(len(expanded)):
        assert expanded.array[i] == any(pattern.array[i : i + n + 1])


@given(bool_concatenation(), integers(min_value=0))
def test_concatenation(concatenated, n):
    expanded, excess = expand_left(concatenated, n)
    assert len(expanded) == len(concatenated)
    obtained = expanded.to_pattern().array
    expected = expand_left(concatenated.to_pattern(), n)[0].to_pattern().array
    assert np.array_equal(
        obtained, expected
    ), f"Obtained: {obtained}\nExpected: {expected}"

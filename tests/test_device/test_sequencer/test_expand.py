import numpy as np
from hypothesis import given
from hypothesis.strategies import integers

from caqtus.device.sequencer.compilation.broaden import broaden_left
from caqtus.device.sequencer.instructions import Concatenated, Pattern, Repeated
from .generate_concatenate import bool_concatenation
from .generate_pattern import bool_pattern
from .generate_repeat import bool_repeated


@given(bool_pattern(), integers(min_value=0))
def test_pattern(pattern, n):
    expanded, excess = broaden_left(pattern, n)
    assert len(expanded) == len(pattern)
    for i in range(len(expanded)):
        assert expanded.array[i] == any(pattern.array[i : i + n + 1])


def test_pattern_0():
    pattern = Pattern([False, True])
    expanded, excess = broaden_left(pattern, 1)
    assert expanded == Pattern([True, True])
    assert excess == 0


@given(bool_concatenation(), integers(min_value=0))
def test_concatenation(concatenated, n):
    expanded, excess = broaden_left(concatenated, n)
    assert len(expanded) == len(concatenated)
    obtained = expanded.to_pattern().array
    expected = broaden_left(concatenated.to_pattern(), n)[0].to_pattern().array
    assert np.array_equal(
        obtained, expected
    ), f"Obtained: {obtained}\nExpected: {expected}"


def test_0():
    instr = Concatenated(Pattern([False]), Pattern([False, True]))
    expanded, excess = broaden_left(instr, 1)
    assert expanded == Pattern([False, True, True])
    assert excess == 0


@given(bool_repeated(), integers(min_value=0))
def test_repeated(repeated, n):
    expanded, excess = broaden_left(repeated, n)
    assert len(expanded) == len(repeated)
    obtained = expanded.to_pattern().array
    expected = broaden_left(repeated.to_pattern(), n)[0].to_pattern().array
    assert np.array_equal(
        obtained, expected
    ), f"Obtained: {obtained}\nExpected: {expected}"


def test_1():
    instr = Pattern([False, True]) * 10
    expanded, excess = broaden_left(instr, 1)
    assert expanded == Pattern([True, True]) * 10


def test_2():
    instr = Pattern([False, False, True]) * 10 + Pattern([False, True])
    expanded, excess = broaden_left(instr, 1)
    assert excess == 0
    assert expanded == Pattern([False, True, True]) * 10 + Pattern([True, True])

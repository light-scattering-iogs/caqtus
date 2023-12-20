import numpy as np
import pytest
from hypothesis import given, settings, Verbosity
from hypothesis.strategies import composite, integers

from sequencer.instructions.struct_array_instruction import Pattern, Concatenate
from .generate_concatenate import generate_concatenate


@composite
def interval(draw, length: int) -> tuple[int, int]:
    start = draw(integers(min_value=0, max_value=length))
    stop = draw(integers(min_value=start, max_value=length))
    return start, stop


@composite
def concatenation_and_interval(draw) -> tuple[Concatenate, tuple[int, int]]:
    length = draw(integers(min_value=2, max_value=100))
    instr = draw(generate_concatenate(length))
    s = draw(interval(length))
    return instr, s


@given(concatenation_and_interval())
def test_slicing(args):
    instr, (start, stop) = args
    assert instr[start:stop].to_pattern() == instr.to_pattern()[start:stop]


@composite
def two_concatenations(draw) -> tuple[Concatenate, Concatenate]:
    length = draw(integers(min_value=2, max_value=100))
    instr1 = draw(generate_concatenate(length))
    instr2 = draw(generate_concatenate(length))
    return instr1, instr2


@given(two_concatenations())
def test_merge(args):
    instr1, instr2 = args
    merged = instr1.merge_channels(instr2)
    assert merged.get_channel("f0").to_pattern() == instr1.to_pattern()
    assert merged.get_channel("f1").to_pattern() == instr2.to_pattern()
    assert merged.depth == 1
    print(instr1)
    print(instr2)
    print(merged)


def test_slicing_1():
    instr = Pattern([0, 1]) + Pattern([0])
    assert instr[1:2].to_pattern() == Pattern([1])


def test_slicing_2():
    instr = Pattern([0]) + Pattern([1])
    assert instr[0:2].to_pattern() == Pattern([0, 1])


def test_slicing_3():
    instr = Pattern([0]) + Pattern([1])
    assert instr[2:2].to_pattern() == instr.to_pattern()[2:2]


def test():
    dtype = np.dtype([("a", np.int32)])
    a = Pattern([1, 2, 3], dtype=dtype)
    b = Pattern([4, 5, 6])
    c = Pattern([7, 8, 9])
    with pytest.raises(TypeError):
        a + b
    assert (b + c + b).depth == 1

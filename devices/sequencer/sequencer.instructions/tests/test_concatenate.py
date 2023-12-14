import numpy as np
import pytest
from hypothesis import given
from hypothesis.strategies import composite, integers

from sequencer.instructions.struct_array_instruction import Pattern, Concatenate


@composite
def flat_concatenation(draw, length: int) -> Concatenate:
    if length <= 1:
        raise ValueError("Length must be strictly greater than 1.")
    else:
        left_length = draw(integers(min_value=1, max_value=length - 1))
        right_length = length - left_length

        left = Pattern([i for i in range(left_length)])
        if right_length == 1:
            right = Pattern([left_length])
        else:
            right = draw(flat_concatenation(right_length))
        return left + right


@composite
def interval(draw, length: int) -> tuple[int, int]:
    start = draw(integers(min_value=0, max_value=length))
    stop = draw(integers(min_value=start, max_value=length))
    return start, stop


@given(flat_concatenation(length=100), interval(length=100))
def test_slicing(instr: Concatenate, interval):
    start, stop = interval
    assert instr[start:stop].to_pattern() == instr.to_pattern()[start:stop]


def test():
    dtype = np.dtype([("a", np.int32)])
    a = Pattern([1, 2, 3], dtype=dtype)
    b = Pattern([4, 5, 6])
    c = Pattern([7, 8, 9])
    with pytest.raises(TypeError):
        a + b
    assert (b + c + b).depth == 1
    print(str(b + c))
    print((b + c)[0:5].to_pattern())

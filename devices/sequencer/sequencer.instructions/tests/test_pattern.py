import numpy as np
from hypothesis import given

from sequencer.instructions.struct_array_instruction import Pattern
from hypothesis.strategies import composite, integers
from .generate_concatenate import generate_concatenate
from .generate_pattern import generate_pattern


def test():
    a = Pattern([1, 2, 3])
    assert a[0] == 1
    assert a[0:2] == Pattern([1, 2])


@composite
def draw_concatenation_and_pattern(draw, max_length: int):
    length = draw(integers(min_value=2, max_value=max_length))
    concatenation = draw(generate_concatenate(length))
    pattern = generate_pattern(length)
    return concatenation, pattern


@given(draw_concatenation_and_pattern(max_length=100))
def test_merge(args):
    concatenation = args[0].as_type(np.dtype([("f1", np.int64)]))
    pattern = args[1].as_type(np.dtype([("f0", np.int64)]))
    merged = pattern.merge_channels(concatenation)
    assert merged.get_channel("f0").to_pattern() == pattern
    assert merged.get_channel("f1").to_pattern() == concatenation.to_pattern()
    assert merged.depth == 0

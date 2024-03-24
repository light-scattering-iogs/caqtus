from caqtus.device.sequencer.instructions import Pattern, stack_instructions, with_name
from hypothesis import given
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
    concatenation = args[0]
    pattern = args[1]
    merged = stack_instructions(
        [with_name(pattern, "f0"), with_name(concatenation, "f1")]
    )
    assert merged["f0"].to_pattern() == pattern
    assert merged["f1"].to_pattern() == concatenation.to_pattern()
    assert merged.depth == 0

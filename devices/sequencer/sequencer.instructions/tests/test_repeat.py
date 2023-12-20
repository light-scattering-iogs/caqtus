from hypothesis import given
from hypothesis.strategies import composite, integers

from sequencer.instructions.struct_array_instruction import Repeat, Pattern
from .generate_repeat import generate_repeat


@composite
def interval(draw, length: int) -> tuple[int, int]:
    start = draw(integers(min_value=0, max_value=length))
    stop = draw(integers(min_value=start, max_value=length))
    return start, stop


@composite
def repeat_and_interval(draw) -> tuple[Repeat, tuple[int, int]]:
    instr = draw(generate_repeat(100, 100))
    s = draw(interval(len(instr)))
    return instr, s


@given(repeat_and_interval())
def test_slicing(args):
    instr, (start, stop) = args
    assert instr[start:stop].to_pattern() == instr.to_pattern()[start:stop]


def test_1():
    b = 2 * Pattern([0])
    assert b[0:1] == Pattern([0])

from hypothesis import given
from hypothesis.strategies import composite, integers

from caqtus.shot_compilation.timed_instructions import (
    Repeated,
    Pattern,
    merge_instructions,
)
from .generate_repeat import generate_repeat, generate_repeat_fixed_length


@composite
def interval(draw, length: int) -> tuple[int, int]:
    start = draw(integers(min_value=0, max_value=length))
    stop = draw(integers(min_value=start, max_value=length))
    return start, stop


@composite
def repeat_and_interval(draw) -> tuple[Repeated, tuple[int, int]]:
    instr = draw(generate_repeat(100, 100))
    s = draw(interval(len(instr)))
    return instr, s


@composite
def draw_two_repeat(draw, max_length: int) -> tuple[Repeated, Repeated]:
    length = draw(integers(min_value=2, max_value=max_length))
    instr1 = draw(generate_repeat_fixed_length(length))
    instr2 = draw(generate_repeat_fixed_length(length))
    return instr1, instr2


@given(draw_two_repeat(100))
def test_merge_1(args):
    repeat1 = args[0]
    repeat2 = args[1]
    merged = merge_instructions(f0=repeat1, f1=repeat2)
    assert merged["f0"].to_pattern() == repeat1.to_pattern()
    assert merged["f1"].to_pattern() == repeat2.to_pattern()


def test_merge_2():
    repeat1 = 4 * Pattern([0, 1])
    repeat2 = 2 * Pattern([0, 1, 2, 3])
    merged = merge_instructions(f0=repeat1, f1=repeat2)
    assert merged["f0"].to_pattern() == repeat1.to_pattern()
    assert merged["f1"].to_pattern() == repeat2.to_pattern()


def test_merge_3():
    repeat_1 = 6 * Pattern([0, 1])
    repeat_2 = 4 * Pattern([0, 1, 2])
    stacked = merge_instructions(f0=repeat_1, f1=repeat_2)
    assert stacked["f0"] == Pattern([0, 1, 0, 1, 0, 1]) * 2
    assert stacked["f1"] == Pattern([0, 1, 2, 0, 1, 2]) * 2


@given(repeat_and_interval())
def test_slicing_1(args):
    instr, (start, stop) = args
    assert instr[start:stop].to_pattern() == instr.to_pattern()[start:stop]


def test_slicing_2():
    b = 3 * Pattern([0])
    assert b[0:3] == b, str(b[0:3])


def test_slicing_3():
    b = 2 * Pattern([0, 1])
    assert b[0:1] == Pattern([0]), str(b[0:1])


def test_slicing_4():
    b = 2 * Pattern([0, 1])
    assert b[1:1] == Pattern([]), str(b[1:1])


def test_slicing_5():
    b = 2 * Pattern([0, 1, 2])
    assert b[1:2] == Pattern([1]), str(b[1:2])


def test_slicing_6():
    b = 2 * Pattern([0, 1])
    assert b[1:2] == Pattern([1]), str(b[1:2])


def test_1():
    b = 2 * Pattern([0])
    assert b[0:1] == Pattern([0])


if __name__ == "__main__":
    test_merge_3()

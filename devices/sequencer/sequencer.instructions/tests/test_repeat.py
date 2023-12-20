from hypothesis import given
from hypothesis.strategies import composite, integers

from sequencer.instructions.struct_array_instruction import Pattern, Concatenate, Repeat


@composite
def flat_repeat(draw, max_repetitions: int, max_sub_instruction_length) -> Repeat:
    repetitions = draw(integers(min_value=2, max_value=max_repetitions))
    sub_instruction_length = draw(
        integers(min_value=1, max_value=max_sub_instruction_length)
    )

    instr = Pattern([i for i in range(sub_instruction_length)])
    return repetitions * instr


@composite
def interval(draw, length: int) -> tuple[int, int]:
    start = draw(integers(min_value=0, max_value=length))
    stop = draw(integers(min_value=start, max_value=length))
    return start, stop


@composite
def repeat_and_interval(draw) -> tuple[Repeat, tuple[int, int]]:
    instr = draw(flat_repeat(100, 100))
    s = draw(interval(len(instr)))
    return instr, s


@given(repeat_and_interval())
def test_slicing(args):
    instr, (start, stop) = args
    assert instr[start:stop].to_pattern() == instr.to_pattern()[start:stop]

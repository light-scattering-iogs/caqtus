import numpy as np
from hypothesis import given
from hypothesis.strategies import composite, booleans, integers

from sequencer.instructions.base_instructions import (
    Pattern,
    SequenceInstruction,
    leaves,
)


@composite
def pattern(draw):
    length = draw(integers(min_value=0, max_value=10))
    return Pattern(np.arange(length))


@composite
def add(draw, depth: int):
    shortest_length = draw(integers(min_value=0, max_value=depth))
    if draw(booleans()):
        return draw(fixed_depth_instruction(depth=depth - 1)) + draw(
            fixed_depth_instruction(depth=shortest_length)
        )
    else:
        return draw(fixed_depth_instruction(depth=shortest_length)) + draw(
            fixed_depth_instruction(depth=depth - 1)
        )


@composite
def multiply(draw, depth: int):
    return draw(integers(min_value=0, max_value=10)) * draw(
        fixed_depth_instruction(depth=depth - 1)
    )


@composite
def fixed_depth_instruction(draw, depth: int):
    if depth == 0:
        return draw(pattern())
    else:
        if draw(booleans()):
            return draw(multiply(depth=depth))
        else:
            return draw(add(depth=depth))


@composite
def instruction(draw, max_depth: int):
    return draw(
        fixed_depth_instruction(depth=draw(integers(min_value=0, max_value=max_depth)))
    )


@given(instruction(max_depth=5), instruction(max_depth=5))
def test_addition(left, right):
    s = left + right
    assert np.all(s.flatten() == np.concatenate([left.flatten(), right.flatten()]))


@composite
def instruction_and_slice(draw, max_depth: int):
    instr = draw(instruction(max_depth=max_depth))
    start = draw(integers(min_value=0, max_value=len(instr)))
    stop = draw(integers(min_value=start, max_value=len(instr)))
    return instr, start, stop


@given(
    instruction_and_slice(max_depth=6),
)
def test_slice(args):
    instr, start, stop = args
    assert np.all(instr[start:stop].flatten() == instr.flatten()[start:stop])


@given(instruction(max_depth=5))
def test_dtype(instr: SequenceInstruction):
    l = leaves(instr)
    if len(l) > 0:
        assert all(l[0].dtype is leaf.dtype for leaf in l)

import numpy as np
from hypothesis import given
from hypothesis.strategies import composite, lists, floats, booleans, integers

from sequencer.instructions.base_instructions import Pattern


@composite
def pattern(draw):
    values = draw(
        lists(
            floats(allow_nan=False, allow_infinity=False),
            min_size=0,
        )
    )
    return Pattern(np.array(values))


@composite
def add(draw, depth: int):
    shortest_length = draw(integers(min_value=0, max_value=depth))
    if draw(booleans()):
        return draw(fixed_length_instruction(depth=depth - 1)) + draw(
            fixed_length_instruction(depth=shortest_length)
        )
    else:
        return draw(fixed_length_instruction(depth=shortest_length)) + draw(
            fixed_length_instruction(depth=depth - 1)
        )


@composite
def fixed_length_instruction(draw, depth: int):
    if depth == 0:
        return draw(pattern())
    else:
        return draw(add(depth=depth))


@composite
def instruction(draw, max_depth: int):
    return draw(
        fixed_length_instruction(depth=draw(integers(min_value=0, max_value=max_depth)))
    )


@given(instruction(max_depth=5), instruction(max_depth=5))
def test_addition(left, right):
    s = left + right
    assert list(s) == list(left) + list(right)


@composite
def instruction_and_slice(draw, max_depth: int):
    instr = draw(instruction(max_depth=max_depth))
    start = draw(integers(min_value=0, max_value=len(instr)))
    stop = draw(integers(min_value=start, max_value=len(instr)))
    return instr, start, stop


@given(
    instruction_and_slice(max_depth=5),
)
def test_slice(args):
    instr, start, stop = args
    assert list(instr[start:stop]) == list(instr)[start:stop]


# class InstructionOperationsVerification(RuleBasedStateMachine):
#     def __init__(self):
#         super().__init__()
#         self.instruction = Pattern(np.empty(0))
#
#     @rule
#     def perform_operation(self):

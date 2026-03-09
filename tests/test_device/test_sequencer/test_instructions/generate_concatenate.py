import numpy as np
from hypothesis.strategies import composite, integers, SearchStrategy, lists

from caqtus.shot_compilation.timed_instructions import (
    TimedInstruction,
    concatenate,
    InstrType,
)
from .generate_pattern import generate_pattern


@composite
def generate_concatenate(
    draw, length: int, offset: int = 0
) -> TimedInstruction[np.int64]:
    if length <= 1:
        raise ValueError("Length must be strictly greater than 1.")
    else:
        left_length = draw(integers(min_value=1, max_value=length - 1))
        right_length = length - left_length

        left = generate_pattern(left_length, offset=offset)
        if right_length == 1:
            right = generate_pattern(right_length, offset=offset + left_length)
        else:
            right = draw(
                generate_concatenate(right_length, offset=offset + left_length)
            )
        return left + right


def concatenation(
    children: SearchStrategy[TimedInstruction[InstrType]],
    min_size: int = 2,
    max_size: int = 50,
) -> SearchStrategy[TimedInstruction[InstrType]]:
    # We can't guarantee that the generated instructions will be a concatenation
    # because concatenate might normalize the instruction.
    return lists(children, min_size=min_size, max_size=max_size).map(
        lambda x: concatenate(*x)
    )

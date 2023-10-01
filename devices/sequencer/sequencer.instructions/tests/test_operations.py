import logging

import numpy as np
from hypothesis import given
from hypothesis.strategies import composite, booleans, integers, permutations
from sympy import factorint

from sequencer.instructions.base_instructions import (
    Pattern,
    SequenceInstruction,
    number_operations,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@composite
def factorize(draw, number: int) -> tuple[int, int]:
    if number <= 1:
        raise ValueError("Number must be greater than 1.")
    factors = factorint(number)
    flat_factors = []
    for factor, exponent in factors.items():
        flat_factors.extend([factor] * exponent)
    if len(flat_factors) == 1:
        return 1, number
    else:
        flat_factors = draw(permutations(flat_factors))
        a_length = draw(integers(min_value=1, max_value=len(flat_factors) - 1))
        a = int(np.prod(flat_factors[:a_length]))
        b = int(np.prod(flat_factors[a_length:]))
        return min(a, b), max(a, b)


def construct_pattern(length: int) -> Pattern:
    return Pattern(np.arange(length))


@composite
def fixed_depth_instruction(draw, length: int, depth: int) -> SequenceInstruction:
    if not (length >= depth >= 0):
        raise ValueError("Invalid length or depth.")
    if depth == 0:
        if length != 0:
            raise ValueError("Invalid length or depth.")
        return construct_pattern(length)
    if depth == 1:
        return construct_pattern(length)
    else:
        if draw(booleans()):
            a, b = draw(factorize(length))
            if a != 1:
                if depth - 1 <= b:
                    return draw(fixed_depth_instruction(depth=depth - 1, length=b)) * a
        deepest_length = draw(integers(min_value=depth - 1, max_value=length - 1))
        deepest_instruction = draw(
            fixed_depth_instruction(depth=depth - 1, length=deepest_length)
        )

        shallowest_length = length - deepest_length
        shallowest_depth = draw(integers(min_value=1, max_value=shallowest_length))
        shallowest_instruction = draw(
            fixed_depth_instruction(
                depth=shallowest_depth,
                length=shallowest_length,
            )
        )
        if draw(booleans()):
            return deepest_instruction + shallowest_instruction
        else:
            return shallowest_instruction + deepest_instruction


@composite
def instruction(draw, max_length: int, max_depth: int):
    if not (max_length >= max_depth >= 0):
        raise ValueError("Invalid length or depth.")
    length = draw(integers(min_value=0, max_value=max_length))
    if length == 0:
        depth = 0
    else:
        depth = draw(integers(min_value=1, max_value=length))
    return draw(fixed_depth_instruction(length=length, depth=depth))


@given(
    instruction(max_length=100, max_depth=5), instruction(max_length=100, max_depth=5)
)
def test_addition(left, right):
    s = left + right
    assert np.all(s.flatten() == np.concatenate([left.flatten(), right.flatten()]))


@given(instruction(max_length=100, max_depth=5), integers(min_value=1, max_value=10))
def test_multiplication(instr, n):
    s = instr * n
    assert np.all(s.flatten() == np.concatenate([instr.flatten()] * n))


@composite
def instruction_and_slice(draw, max_length: int, max_depth: int):
    instr = draw(instruction(max_length=max_length, max_depth=max_depth))
    start = draw(integers(min_value=0, max_value=len(instr)))
    stop = draw(integers(min_value=start, max_value=len(instr)))
    return instr, start, stop


@given(
    instruction_and_slice(max_length=100, max_depth=6),
)
def test_slice(args):
    instr, start, stop = args
    assert np.all(instr[start:stop].flatten() == instr.flatten()[start:stop])


@given(instruction(max_length=100, max_depth=5))
def test_invariants(instr: SequenceInstruction):
    assert number_operations(instr) <= len(instr)

import heapq
import math
from collections.abc import Sequence

import numpy
from multipledispatch import dispatch
from numpy.typing import DTypeLike

from caqtus.utils.itertools import pairwise
from ._instructions import (
    SequencerInstruction,
    Pattern,
    Concatenated,
    Repeated,
    empty_like,
    concatenate,
)


def stack_instructions(
    instructions: Sequence[SequencerInstruction],
) -> SequencerInstruction:
    """Stack several instructions along their dtype names."""

    # This uses a divide-and-conquer approach to merge the instructions.
    # Another approach is to stack the instructions into a single accumulator, but
    # it seems to give worse performance.

    if len(instructions) == 1:
        return instructions[0]
    elif len(instructions) == 2:
        return stack(instructions[0], instructions[1])
    else:
        length = len(instructions) // 2
        sub_block_1 = stack_instructions(instructions[:length])
        sub_block_2 = stack_instructions(instructions[length:])
        return stack(sub_block_1, sub_block_2)


@dispatch(SequencerInstruction, SequencerInstruction)
def stack(a: SequencerInstruction, b: SequencerInstruction) -> SequencerInstruction:
    if len(a) != len(b):
        raise ValueError("Instructions must have the same length")

    if a.dtype.fields is None:
        raise ValueError("Instruction must have at least one channel")

    if b.dtype.fields is None:
        raise ValueError("Instruction must have at least one channel")

    return _stack_patterns(a.to_pattern(), b.to_pattern())


def _stack_patterns(a: Pattern, b: Pattern) -> Pattern:
    merged_dtype = merge_dtypes(a.dtype, b.dtype)
    merged = numpy.empty(len(a), dtype=merged_dtype)
    for name in a.dtype.names:
        merged[name] = a.array[name]
    for name in b.dtype.names:
        merged[name] = b.array[name]
    return Pattern.create_without_copy(merged)


@dispatch(Concatenated, Concatenated)
def stack(a: Concatenated, b: Concatenated) -> SequencerInstruction:
    if len(a) != len(b):
        raise ValueError("Instructions must have the same length")
    new_bounds = heapq.merge(a._instruction_bounds, b._instruction_bounds)
    results = []
    for start, stop in pairwise(new_bounds):
        results.append(stack(a[start:stop], b[start:stop]))
    if not results:
        return stack(empty_like(a), empty_like(b))
    return concatenate(*results)


@dispatch(Concatenated, SequencerInstruction)
def stack(a: Concatenated, b: SequencerInstruction) -> SequencerInstruction:
    if len(a) != len(b):
        raise ValueError("Instructions must have the same length")

    results = []
    for (start, stop), instruction in zip(
        pairwise(a._instruction_bounds), a.instructions
    ):
        results.append(stack(instruction, b[start:stop]))
    if not results:
        return stack(empty_like(a), empty_like(b))
    return concatenate(*results)


@dispatch(SequencerInstruction, Concatenated)
def stack(a: SequencerInstruction, b: Concatenated) -> SequencerInstruction:
    if len(a) != len(b):
        raise ValueError("Instructions must have the same length")

    results = []
    for (start, stop), instruction in zip(
        pairwise(b._instruction_bounds), b.instructions
    ):
        results.append(stack(a[start:stop], instruction))
    if not results:
        return stack(empty_like(a), empty_like(b))
    return concatenate(*results)


@dispatch(Repeated, Repeated)
def stack(a: Repeated, b: Repeated) -> SequencerInstruction:
    if len(a) != len(b):
        raise ValueError("Instructions must have the same length")
    lcm = math.lcm(len(a.instruction), len(b.instruction))
    if lcm == len(a):
        b_a = tile(a.instruction, a.repetitions)
        b_b = tile(b.instruction, b.repetitions)
    else:
        r_a = lcm // len(a.instruction)
        b_a = a.instruction * r_a
        r_b = lcm // len(b.instruction)
        b_b = b.instruction * r_b
    block = stack(b_a, b_b)
    return block * (len(a) // len(block))


def merge_dtypes[
    S: DTypeLike, T: DTypeLike, U: DTypeLike
](a: numpy.dtype[S], b: numpy.dtype[T]) -> numpy.dtype[U]:
    merged_dtype = numpy.dtype(
        [(name, a[name]) for name in a.names] + [(name, b[name]) for name in b.names]
    )
    return merged_dtype


def tile[
    T: DTypeLike
](instruction: SequencerInstruction[T], repetitions: int) -> SequencerInstruction[T]:
    return concatenate(*([instruction] * repetitions))

import heapq
import math

import multipledispatch
import numpy as np

from caqtus.utils.itertools import pairwise
from ._instructions import (
    SequencerInstruction,
    Pattern,
    Concatenated,
    Repeated,
    empty_like,
    concatenate,
)
from ._with_name import with_name


def merge_instructions(**instructions: SequencerInstruction) -> SequencerInstruction:
    """Merge several instructions by name.

    This function finds a common structure to the different instructions and produces
    a single instruction with parallel fields for each input instruction.

    Args:
        instructions: The instructions to merge by name.
            There must be at least one instruction.
            They must all have the same length.

    Returns:
        A new instruction with the same length as the input instructions,
        and a structured dtype with a field for each input instruction.

    Warning:
        If the input instructions have no simple common structure, this function will
        convert each instruction to an explicit pattern and merge them.
        If the input instructions have a very long length, this function might be slow
        and consume a lot of memory.

    Raises:
        ValueError: If the instructions have different lengths or no instructions are
            provided.
    """

    if not instructions:
        raise ValueError("No instructions to merge")

    # Check that all instructions have the same length
    length = len(next(iter(instructions.values())))
    for instruction in instructions.values():
        if len(instruction) != length:
            raise ValueError("Instructions must have the same length")

    named_instructions = [
        with_name(instruction, name) for name, instruction in instructions.items()
    ]
    return _stack_instructions_no_checks(*named_instructions)


def stack_instructions(
    *instructions: SequencerInstruction[np.void],
) -> SequencerInstruction[np.void]:
    """Stack several instructions along their dtype names.

    Args:
        instructions: A sequence of instructions to stack.
            They must all have the same length.
            They must have a structured dtype with named fields.

    Returns:
        A new instruction with the same length as the input instructions,
        and a dtype that is the union of the input dtypes.
    """

    if not instructions:
        raise ValueError("No instructions to stack")

    # Check that all instructions have the same length
    length = len(instructions[0])
    for instruction in instructions[1:]:
        if len(instruction) != length:
            raise ValueError("Instructions must have the same length")

    # Check that all instructions have a structured dtype
    for instruction in instructions:
        if not issubclass(instruction.dtype.type, np.void):
            raise ValueError("Instruction must have a structured dtype")

    return _stack_instructions_no_checks(*instructions)


def _stack_instructions_no_checks(
    *instructions: SequencerInstruction[np.void],
) -> SequencerInstruction:
    # This uses a divide-and-conquer approach to merge the instructions.
    # Another approach is to stack the instructions into a single accumulator, but
    # it seems to give worse performance on typical uses.

    if len(instructions) == 1:
        return instructions[0]
    elif len(instructions) == 2:
        return stack(instructions[0], instructions[1])
    else:
        length = len(instructions) // 2
        sub_block_1 = _stack_instructions_no_checks(*instructions[:length])
        sub_block_2 = _stack_instructions_no_checks(*instructions[length:])
        return stack(sub_block_1, sub_block_2)


stack = multipledispatch.Dispatcher("stack")


@stack.register(SequencerInstruction, SequencerInstruction)
def stack_generic(
    a: SequencerInstruction[np.void], b: SequencerInstruction[np.void]
) -> SequencerInstruction:
    assert len(a) == len(b)
    return _stack_patterns(a.to_pattern(), b.to_pattern())


def _stack_patterns(a: Pattern[np.void], b: Pattern[np.void]) -> Pattern[np.void]:
    merged_dtype = merge_dtypes(a.dtype, b.dtype)
    merged = np.zeros(len(a), dtype=merged_dtype)

    assert a.dtype.names is not None
    for name in a.dtype.names:
        merged[name] = a.array[name]

    assert b.dtype.names is not None
    for name in b.dtype.names:
        merged[name] = b.array[name]
    return Pattern.create_without_copy(merged)


@stack.register(Concatenated, Concatenated)
def stack_concatenations(a: Concatenated, b: Concatenated) -> SequencerInstruction:
    assert len(a) == len(b)

    new_bounds = heapq.merge(a._instruction_bounds, b._instruction_bounds)
    results = []
    for start, stop in pairwise(new_bounds):
        results.append(stack(a[start:stop], b[start:stop]))
    if not results:
        return stack(empty_like(a), empty_like(b))
    return concatenate(*results)


@stack.register(Concatenated, SequencerInstruction)
def stack_concatenation_left(
    a: Concatenated, b: SequencerInstruction
) -> SequencerInstruction:
    assert len(a) == len(b)

    results = []
    for (start, stop), instruction in zip(
        pairwise(a._instruction_bounds), a.instructions
    ):
        results.append(stack(instruction, b[start:stop]))
    if not results:
        return stack(empty_like(a), empty_like(b))
    return concatenate(*results)


@stack.register(SequencerInstruction, Concatenated)
def stack_concatenation_right(
    a: SequencerInstruction, b: Concatenated
) -> SequencerInstruction:
    assert len(a) == len(b)

    results = []
    for (start, stop), instruction in zip(
        pairwise(b._instruction_bounds), b.instructions
    ):
        results.append(stack(a[start:stop], instruction))
    if not results:
        return stack(empty_like(a), empty_like(b))
    return concatenate(*results)


@stack.register(Repeated, Repeated)
def stack_repeated(a: Repeated, b: Repeated) -> SequencerInstruction:
    assert len(a) == len(b)

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


def merge_dtypes(a: np.dtype[np.void], b: np.dtype[np.void]) -> np.dtype[np.void]:
    assert a.names is not None
    assert b.names is not None
    merged_dtype = np.dtype(
        [(name, a[name]) for name in a.names] + [(name, b[name]) for name in b.names]
    )
    return merged_dtype


def tile[
    T: np.generic
](instruction: SequencerInstruction[T], repetitions: int) -> SequencerInstruction[T]:
    return concatenate(*([instruction] * repetitions))

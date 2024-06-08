import functools

import numpy as np

from ..instructions import (
    SequencerInstruction,
    Pattern,
    Concatenated,
    concatenate,
    Repeated,
)


@functools.singledispatch
def expand_left(
    instruction: SequencerInstruction[bool], n: int
) -> tuple[SequencerInstruction[bool], int]:
    """Expand the instruction to the left by n steps.

    Returns:
        A tuple (result, excess) where:
        - result: The expanded instruction.
            result[i] = any(instruction[i:i+n+1])
        - excess: The number of steps before this instruction that must be set to True.
            excess = max(0, n - first)
            where first is the index of the first True value in the instruction if it
            exists, otherwise excess = 0.

    """

    raise NotImplementedError(
        f"Don't know how to expand instruction of type {type(instruction)}"
    )


@expand_left.register
def expand_pattern_left(instruction: Pattern, n: int):
    if not instruction.dtype == np.bool_:
        raise TypeError("Instruction must have dtype bool")
    pulse_length = min(len(instruction), n + 1)
    pulse = np.full(pulse_length, True)
    convolution = np.convolve(instruction.array, pulse)
    result = convolution[pulse_length - 1 :]
    high_indices = instruction.array.nonzero()[0]
    if len(high_indices) == 0:
        excess = 0
    else:
        first_high_index = int(high_indices[0])  # need to avoid numpy integers
        excess = max(0, n - first_high_index)
    return Pattern.create_without_copy(result), excess


@expand_left.register
def expand_concatenated_left(instruction: Concatenated, n: int):
    new_instructions = []
    bleed = 0
    for sub_instruction in reversed(instruction.instructions):
        expanded, new_bleed = expand_left(sub_instruction, n)
        overwritten_length = min(bleed, len(expanded))
        overwritten = Pattern([True]) * overwritten_length
        new_instructions.append(overwritten)
        kept = expanded[: len(expanded) - len(overwritten)]
        new_instructions.append(kept)
        bleed -= len(expanded)
        bleed = max(new_bleed, bleed)
    return concatenate(*reversed(new_instructions)), bleed


@expand_left.register
def expand_repeated_left(repeated: Repeated, n: int):
    expanded, bleed = expand_left(repeated.instruction, n)
    if bleed == 0:
        return expanded * repeated.repetitions, bleed
    overwritten_length = min(bleed, len(expanded))
    overwritten = Pattern([True]) * overwritten_length
    kept = expanded[: len(expanded) - len(overwritten)]
    instr = (kept + overwritten) * (repeated.repetitions - 1) + expanded
    return instr, bleed

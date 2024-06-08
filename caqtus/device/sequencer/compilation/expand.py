import functools

import numpy as np

from ..instructions import SequencerInstruction, Pattern


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
    high_indices = result.nonzero()[0]
    if len(high_indices) == 0:
        excess = 0
    else:
        first_high_index = high_indices[0]
        excess = max(0, n - first_high_index)
    return Pattern.create_without_copy(result), excess

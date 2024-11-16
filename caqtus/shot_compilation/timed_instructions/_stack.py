import numpy as np

from ._instructions import CombinedInstruction, LT, merge
from ._with_name import with_name


def merge_instructions(
    **instructions: CombinedInstruction[LT, np.generic]
) -> CombinedInstruction[LT, np.void]:
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
    *instructions: CombinedInstruction[LT, np.void],
) -> CombinedInstruction[LT, np.void]:
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
    *instructions: CombinedInstruction[LT, np.void],
) -> CombinedInstruction[LT, np.void]:
    # This uses a divide-and-conquer approach to merge the instructions.
    # Another approach is to stack the instructions into a single accumulator, but
    # it seems to give worse performance on typical uses.

    if len(instructions) == 1:
        return instructions[0]
    elif len(instructions) == 2:
        return merge(instructions[0], (instructions[1]))
    else:
        length = len(instructions) // 2
        sub_block_1 = _stack_instructions_no_checks(*instructions[:length])
        sub_block_2 = _stack_instructions_no_checks(*instructions[length:])
        return merge(sub_block_1, sub_block_2)

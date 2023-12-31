from collections.abc import Sequence

from ._instructions import SequencerInstruction


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
        return instructions[0].merge_channels(instructions[1])
    else:
        length = len(instructions) // 2
        sub_block_1 = stack_instructions(instructions[:length])
        sub_block_2 = stack_instructions(instructions[length:])
        return sub_block_1.merge_channels(sub_block_2)

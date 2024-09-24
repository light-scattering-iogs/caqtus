import numpy as np

from ._instructions import SequencerInstruction


def with_name(
    instruction: SequencerInstruction, name: str
) -> SequencerInstruction[np.void]:
    """
    Change the dtype of the instruction into a structured array with a single field
    with the given name and the same dtype as the original instruction.
    """

    new_type = np.dtype([(name, instruction.dtype)])
    return instruction.as_type(new_type)

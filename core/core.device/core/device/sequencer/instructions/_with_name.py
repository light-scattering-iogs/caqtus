from typing import TypeVar

import numpy as np

from ._instructions import SequencerInstruction

_T = TypeVar("_T")


def with_name(
    instruction: SequencerInstruction[_T], name: str
) -> SequencerInstruction[_T]:
    """
    Change the dtype of the instruction into a structured array with a single field
    with the given name and the same dtype as the original instruction.
    """

    new_type = np.dtype([(name, instruction.dtype)])
    return instruction.as_type(new_type)

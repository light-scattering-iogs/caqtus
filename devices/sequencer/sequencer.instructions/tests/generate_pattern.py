import numpy as np

from sequencer.instructions.struct_array_instruction import Pattern


def generate_pattern(length: int, offset: int = 0) -> Pattern:
    return Pattern(np.arange(offset, offset + length))

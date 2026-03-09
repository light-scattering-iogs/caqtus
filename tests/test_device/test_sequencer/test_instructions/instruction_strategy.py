from typing import Optional

import numpy as np
from hypothesis.strategies import SearchStrategy, recursive

from caqtus.shot_compilation.timed_instructions import TimedInstruction, InstrType
from .generate_concatenate import concatenation
from .generate_pattern import pattern
from .generate_repeat import repeated


def instruction(
    leaf_strategy: SearchStrategy[TimedInstruction[InstrType]],
    max_leaves: int,
    max_length: Optional[int] = None,
) -> SearchStrategy[TimedInstruction[InstrType]]:
    strategy = recursive(
        leaf_strategy,
        lambda s: concatenation(s) | repeated(s),
        max_leaves=max_leaves,
    )
    if max_length is not None:
        strategy = strategy.filter(lambda x: len(x) <= max_length)
    return strategy


def digital_instruction(
    max_leaves: int = 30, max_length: Optional[int] = None
) -> SearchStrategy[TimedInstruction[np.bool_]]:
    return instruction(
        pattern(dtype=np.bool_, min_length=1, max_length=10), max_leaves, max_length
    )


def analog_instruction(
    max_leaves: int = 20, max_length: Optional[int] = None
) -> SearchStrategy[TimedInstruction[np.floating]]:
    return instruction(
        pattern(dtype=np.float64, min_length=1, max_length=100), max_leaves, max_length
    )

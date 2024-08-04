from typing import TypeVar, Optional

import numpy as np
from hypothesis.strategies import SearchStrategy, recursive
from numpy.typing import DTypeLike

from caqtus.device.sequencer.instructions import SequencerInstruction
from .generate_concatenate import concatenation
from .generate_pattern import pattern
from .generate_repeat import repeated

T = TypeVar("T", bound=DTypeLike)


def instruction(
        leaf_strategy: SearchStrategy[SequencerInstruction[T]], max_leaves: int, max_length: Optional[int] = None
) -> SearchStrategy[SequencerInstruction[T]]:
    strategy = recursive(
        leaf_strategy,
        lambda s: concatenation(s) | repeated(s),
        max_leaves=max_leaves,
    )
    if max_length is not None:
        strategy = strategy.filter(lambda x: len(x) <= max_length)
    return strategy


def digital_instruction(
        max_leaves: int = 100, max_length: Optional[int] = None
) -> SearchStrategy[SequencerInstruction[np.bool_]]:
    return instruction(pattern(dtype=np.bool_, min_length=1, max_length=10), max_leaves, max_length)


def analog_instruction(
        max_leaves: int = 20,
) -> SearchStrategy[SequencerInstruction[np.floating]]:
    return instruction(
        pattern(dtype=np.float64, min_length=1, max_length=100), max_leaves
    )

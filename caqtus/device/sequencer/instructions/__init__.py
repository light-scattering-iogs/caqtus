import warnings

from caqtus.shot_compilation.timed_instructions import (
    TimedInstruction,
    Concatenated,
    Repeated,
    Pattern,
    convert_to_change_arrays,
    with_name,
    stack_instructions,
    merge_instructions,
    concatenate,
    create_ramp,
    Ramp,
    plot_instruction,
    to_graph,
)

warnings.warn(
    "caqtus.device.sequencer.instructions is deprecated, use "
    "caqtus.shot_compilation.timed_instructions instead.",
    DeprecationWarning,
    stacklevel=2,
)

SequencerInstruction = TimedInstruction

__all__ = [
    "SequencerInstruction",
    "TimedInstruction",
    "Concatenated",
    "Repeated",
    "Pattern",
    "convert_to_change_arrays",
    "with_name",
    "stack_instructions",
    "merge_instructions",
    "concatenate",
    "create_ramp",
    "Ramp",
    "plot_instruction",
    "to_graph",
]

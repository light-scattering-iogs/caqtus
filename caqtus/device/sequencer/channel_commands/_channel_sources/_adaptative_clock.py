import functools

from caqtus.device.sequencer.instructions import (
    SequencerInstruction,
    Pattern,
    Concatenated,
    concatenate,
    Repeated,
    Ramp,
)


@functools.singledispatch
def get_adaptive_clock(
    slave_instruction: SequencerInstruction, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    """Generates a clock signal for a slave instruction."""

    raise NotImplementedError(
        f"Don't know how to generate a clock for an instruction of type "
        f"{type(slave_instruction)}"
    )


@get_adaptive_clock.register
def _(
    target_sequence: Pattern | Ramp, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    return clock_pulse * len(target_sequence)


@get_adaptive_clock.register
def _(
    target_sequence: Concatenated, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    return concatenate(
        *(
            get_adaptive_clock(sequence, clock_pulse)
            for sequence in target_sequence.instructions
        )
    )


@get_adaptive_clock.register
def _(
    target_sequence: Repeated, clock_pulse: SequencerInstruction
) -> SequencerInstruction:
    if len(target_sequence.instruction) == 1:
        return clock_pulse + Pattern([False]) * (
            (len(target_sequence) - 1) * len(clock_pulse)
        )
    else:
        raise NotImplementedError(
            "Only one instruction is supported in a repeat block at the moment"
        )

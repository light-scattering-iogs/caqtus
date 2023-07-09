from collections.abc import Sequence

from sequence.configuration import DigitalLane
from sequencer.channel import ChannelInstruction, ChannelPattern


def compile_digital_lane(
    step_durations: Sequence[float],
    lane: DigitalLane,
    time_step: float,
) -> ChannelInstruction[bool]:
    instructions = []
    for value, start, stop in lane.get_value_spans():
        duration = sum(step_durations[start:stop])
        length = int(duration / time_step)
        instructions.append(ChannelPattern([value]) * length)
    return ChannelInstruction.join(instructions, dtype=bool)

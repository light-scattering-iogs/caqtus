import logging

from experiment_control.compute_device_parameters import (
    compile_step_durations,
    compile_lane,
)
from sequence.configuration import ShotConfiguration
from sequencer.instructions import SequencerInstructionOld, ChannelLabel
from variable.namespace import VariableNamespace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def test_digital_merging(
    shot_config: ShotConfiguration, variables: VariableNamespace
) -> None:
    time_step = 50

    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables,
    )

    lane_names = {
        0: "test trigger",
        1: "532 tweezers (AOM)",
        2: "2D MOT (AOM)",
        3: "Push beam (shutter)",
        4: "MOT coils",
        5: "421 cell vertical (AOM)",
        6: "421 cell (AOM)",
        7: "421 cell horizontal (shutter)",
        8: "421 cell vertical (shutter)",
        9: "626 light (AOM)",
        10: "626 horizontal shutter",
        11: "626 imaging (AOM)",
    }

    lanes = {label: shot_config.find_lane(name) for label, name in lane_names.items()}

    channel_sequences = {
        label: compile_lane(lane, durations, time_step, variables)
        for label, lane in lanes.items()
    }

    sequence = SequencerInstructionOld.from_channel_instruction(
        ChannelLabel(0), channel_sequences.pop(ChannelLabel(0))
    )
    for label, channel_sequence in channel_sequences.items():
        sequence = sequence.add_channel_instruction(label, channel_sequence)

    for label, channel_sequence in channel_sequences.items():
        assert channel_sequence.flatten() == sequence[label].flatten()


def test_analog_merging(
    shot_config: ShotConfiguration, variables: VariableNamespace
) -> None:
    time_step = 2500

    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables,
    )

    lane_names = {
        0: "Tweezers power (AOM)",
        1: "Push power",
        2: "MOT coils current",
    }

    lanes = {label: shot_config.find_lane(name) for label, name in lane_names.items()}

    channel_sequences = {
        label: compile_lane(lane, durations, time_step, variables)
        for label, lane in lanes.items()
    }

    sequence = SequencerInstructionOld.from_channel_instruction(
        ChannelLabel(0), channel_sequences.pop(ChannelLabel(0))
    )
    for label, channel_sequence in channel_sequences.items():
        sequence = sequence.add_channel_instruction(label, channel_sequence)

    for label, channel_sequence in channel_sequences.items():
        assert channel_sequence.flatten() == sequence[label].flatten()

    logger.debug(sequence)

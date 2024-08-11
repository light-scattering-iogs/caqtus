from caqtus.device import DeviceName
from caqtus.device.sequencer import SequencerCompiler
from caqtus.shot_compilation import SequenceContext, ShotContext
from caqtus.shot_compilation.lane_compilers.timing import number_ticks, ns
from .fixtures import (
    time_lanes,
    spincore_config,
    swabian_configuration,
    ni6738_configuration,
    variables,
)


def test_single_digital_lane(
    time_lanes, spincore_config, swabian_configuration, ni6738_configuration, variables
):
    sequence_context = SequenceContext(
        {
            DeviceName("Spincore"): spincore_config,
            DeviceName("Swabian pulse streamer"): swabian_configuration,
            DeviceName("NI6738"): ni6738_configuration,
        },
        time_lanes,
    )
    compilers = {
        name: SequencerCompiler(name, sequence_context)
        for name in sequence_context.get_all_device_configurations()
    }

    shot_context = ShotContext(sequence_context, variables, compilers)
    spincore_sequence = compilers["Spincore"].compile_shot_parameters(shot_context)[
        "sequence"
    ]
    swabian_sequence = compilers["Swabian pulse streamer"].compile_shot_parameters(
        shot_context
    )["sequence"]
    ni6738_sequence = compilers["NI6738"].compile_shot_parameters(shot_context)[
        "sequence"
    ]

    shot_duration = shot_context.get_shot_duration()

    assert len(spincore_sequence) == number_ticks(
        0, shot_duration, spincore_config.time_step * ns
    )
    assert len(swabian_sequence) == number_ticks(
        0.0,
        shot_duration
        + 1.1e-6,  # Need to tak into account time shift when computing shot duration
        swabian_configuration.time_step * ns,
    )
    assert len(ni6738_sequence) == number_ticks(
        0, shot_duration, ni6738_configuration.time_step * ns
    )

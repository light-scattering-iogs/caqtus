from caqtus.device import DeviceName
from caqtus.device.sequencer import SequencerCompiler
from caqtus.shot_compilation import SequenceContext, ShotContext
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
    compilers["Spincore"].compile_shot_parameters(shot_context)
    compilers["Swabian pulse streamer"].compile_shot_parameters(shot_context)
    compilers["NI6738"].compile_shot_parameters(shot_context)

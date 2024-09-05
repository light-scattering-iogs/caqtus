from caqtus.device import DeviceName
from caqtus.device.sequencer import SequencerCompiler
from caqtus.experiment_control._shot_compiler import ShotCompiler
from caqtus.experiment_control.sequence_runner import walk_steps
from caqtus.experiment_control.sequence_runner.sequence_runner import (
    evaluate_initial_context,
)
from caqtus.shot_compilation import SequenceContext
from .device_configurations import configs
from .global_parameters import parameters
from .iterations import iterations
from .time_lanes import time_lanes


def test_0():
    for i, context in enumerate(  # noqa: B007
        walk_steps(iterations.steps, evaluate_initial_context(parameters))
    ):
        if i == 22:
            break
    else:
        raise AssertionError("Loop did not break")
    sequence_context = SequenceContext(configs, time_lanes)
    compiler = ShotCompiler(
        time_lanes,
        configs,
        {
            DeviceName("Spincore"): SequencerCompiler(
                DeviceName("Spincore"), sequence_context
            ),
            DeviceName("NI6738"): SequencerCompiler(
                DeviceName("NI6738"), sequence_context
            ),
        },
    )

    result = compiler.compile_shot_sync(context.variables.dict())
    print(result)

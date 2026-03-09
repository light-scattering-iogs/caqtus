import anyio

from caqtus.device import DeviceName
from caqtus.device.sequencer import SequencerCompiler
from caqtus.device.sequencer.timing import number_time_steps
from caqtus.experiment_control.sequence_execution._shot_compiler import ShotCompiler
from caqtus.experiment_control.sequence_execution._shot_primitives import ShotParameters
from caqtus.shot_compilation import SequenceContext
from caqtus.shot_compilation.timing import to_time
from caqtus.types.iteration import StepsConfiguration
from caqtus.types.iteration._step_context import StepContext
from caqtus.types.parameter import ParameterNamespace

from .device_configurations import configs
from .global_parameters import parameters
from .iterations import iterations
from .time_lanes import time_lanes


async def test_0(anyio_backend):
    # This is an issue encountered in the wild, there was issue with floating point
    # precision.
    # It was solved by using decimal times during shot compilation.
    for i, context in enumerate(  # noqa: B007
        iterations.walk(StepContext(parameters.evaluate()))
    ):
        if i == 22:
            break
    else:
        raise AssertionError("Loop did not break")
    sequence_context = SequenceContext._new(
        configs, StepsConfiguration.empty(), ParameterNamespace.empty(), time_lanes
    )
    compiler = ShotCompiler(
        sequence_context,
        {
            DeviceName("Spincore"): SequencerCompiler(
                DeviceName("Spincore"), sequence_context
            ),
            DeviceName("NI6738"): SequencerCompiler(
                DeviceName("NI6738"), sequence_context
            ),
        },
    )
    params, duration = await compiler.compile_shot(ShotParameters(0, context.variables))
    assert isinstance(duration, float)
    assert duration == 0.47811
    assert len(params[DeviceName("Spincore")]["sequence"]) == number_time_steps(
        to_time(duration), configs[DeviceName("Spincore")].time_step
    )
    assert len(params[DeviceName("NI6738")]["sequence"]) == number_time_steps(
        to_time(duration), configs[DeviceName("NI6738")].time_step
    )

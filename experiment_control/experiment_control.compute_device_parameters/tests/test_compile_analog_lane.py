from experiment_control.compute_device_parameters import (
    compile_step_durations,
    compile_analog_lane,
)
from sequence.configuration import ShotConfiguration, AnalogLane
from variable.namespace import VariableNamespace


def test_compile_analog_lane(
    shot_config: ShotConfiguration, variables: VariableNamespace
) -> None:
    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables,
    )

    time_step = 2.5e-6

    lane = shot_config.find_lane("Tweezers power (AOM)")
    assert isinstance(lane, AnalogLane)
    instruction = compile_analog_lane(
        durations, lane, variables, time_step
    )
    assert len(instruction) == int(sum(durations) / time_step)

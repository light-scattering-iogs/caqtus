from experiment_control.compute_device_parameters import compile_step_durations
from sequence.configuration import ShotConfiguration
from variable.namespace import VariableNamespace


def test_compile_step_durations(shot_config: ShotConfiguration, variables: VariableNamespace) -> None:
    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables,
    )

    assert abs(sum(durations) - 0.3750018) < 1e-12

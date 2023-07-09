from pathlib import Path

import pytest

from experiment_control.compute_device_parameters import compile_step_durations
from parameter_types import Parameter
from sequence.configuration import SequenceConfig, ShotConfiguration
from units import units
from variable.name import DottedVariableName, VariableName
from variable.namespace import VariableNamespace


@pytest.fixture
def sequence_config() -> SequenceConfig:
    path = Path(__file__).parent / "sequence_config.yaml"
    with open(path, "r") as file:
        config = SequenceConfig.from_yaml(file.read())
    return config


@pytest.fixture
def shot_config(sequence_config: SequenceConfig) -> ShotConfiguration:
    return sequence_config.shot_configurations["shot"]


def test_compile_step_durations(shot_config: ShotConfiguration) -> None:
    variables = VariableNamespace[Parameter]()
    variables.update({
        DottedVariableName("ramp_time"): 80 * units[VariableName("ms")],
        DottedVariableName("exposure"): 30 * units[VariableName("ms")],
        DottedVariableName("wait_time"): 1 * units[VariableName("us")],
        DottedVariableName("red_light_duration"): 0.5 * units[VariableName("us")],
        DottedVariableName("kill_duration"): 0.15 * units[VariableName("us")],
    })
    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables,
    )

    assert abs(sum(durations) - 0.3750018) < 1e-12

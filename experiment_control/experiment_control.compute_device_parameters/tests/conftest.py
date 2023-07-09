from pathlib import Path

import pytest

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

@pytest.fixture
def variables(sequence_config: SequenceConfig) -> VariableNamespace[Parameter]:
    variables = VariableNamespace[Parameter]()
    variables.update(
        {
            DottedVariableName("ramp_time"): 80 * units[VariableName("ms")],
            DottedVariableName("exposure"): 30 * units[VariableName("ms")],
            DottedVariableName("wait_time"): 1 * units[VariableName("us")],
            DottedVariableName("red_light_duration"): 0.5 * units[VariableName("us")],
            DottedVariableName("kill_duration"): 0.15 * units[VariableName("us")],
            DottedVariableName("tweezer_power"): 1.,
            DottedVariableName("imaging.tweezer_power"): 0.3,
            DottedVariableName("kill.tweezer_power"): 0.05,
        }
    )
    return variables

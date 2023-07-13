from pathlib import Path

import pytest

from experiment.configuration import ExperimentConfig
from parameter_types import Parameter
from sequence.configuration import SequenceConfig, ShotConfiguration
from units import units, ureg, Quantity
from variable.name import DottedVariableName, VariableName
from variable.namespace import VariableNamespace


@pytest.fixture
def sequence_config() -> SequenceConfig:
    path = Path(__file__).parent / "sequence_config.yaml"
    with open(path, "r") as file:
        config = SequenceConfig.from_yaml(file.read())
    return config


@pytest.fixture
def sequence_config_2() -> SequenceConfig:
    # path = Path(__file__).parent / "test_2_config.yaml"

    path = Path(__file__).parent / "test_short_pulse.yaml"
    with open(path, "r") as file:
        config = SequenceConfig.from_yaml(file.read())
    return config


@pytest.fixture
def experiment_config_2() -> ExperimentConfig:
    path = Path(__file__).parent / "test_2_experiment_config.yaml"
    with open(path, "r") as file:
        config = ExperimentConfig.from_yaml(file.read())
    return config


@pytest.fixture
def variables_2():
    _variables = {
        "ramp_time": Quantity(80, "millisecond"),
        "mot_loading": {
            "red": {
                "power": Quantity(0, "decibel"),
                "frequency": Quantity(-3.2, "megahertz"),
            },
            "current": Quantity(3.6, "ampere"),
            "blue": {
                "power": Quantity(1.0, "dimensionless"),
                "frequency": Quantity(19, "megahertz"),
            },
            "x_current": Quantity(0.47, "ampere"),
            "y_current": Quantity(0, "ampere"),
            "z_current": Quantity(0.3, "ampere"),
        },
        "red_mot": {
            "x_current": Quantity(0.266, "ampere"),
            "y_current": Quantity(0.1, "ampere"),
            "z_current": Quantity(-0.12, "ampere"),
            "frequency": Quantity(-1.17, "megahertz"),
            "power": Quantity(-36, "decibel"),
            "current": Quantity(1, "ampere"),
        },
        "push_power": Quantity(0.5, "milliwatt"),
        "exposure": Quantity(30, "millisecond"),
        "imaging": {
            "x_current": Quantity(0.25, "ampere"),
            "y_current": Quantity(4.94, "ampere"),
            "z_current": Quantity(0.183, "ampere"),
            "tweezer_power": Quantity(0.4, "dimensionless"),
            "power": Quantity(-31, "decibel"),
            "frequency": Quantity(-17.69, "megahertz"),
        },
        "tweezer_power": Quantity(1.0, "dimensionless"),
        "hwp_angle": Quantity(137.5, "dimensionless"),
        "repump_frequency": Quantity(-5, "megahertz"),
        "kill_duration": Quantity(450.578947, "nanosecond"),
        "kill_freq": Quantity(30, "megahertz"),
        "red_light_duration": Quantity(0.5, "microsecond"),
        "red_light_power": Quantity(0, "decibel"),
        "Rabi": {"tweezer_power": Quantity(0.05, "dimensionless")},
        "wait_time": Quantity(1, "microsecond"),
        "kill": {"tweezer_power": Quantity(0.05, "dimensionless")},
        "rep": Quantity(0, "dimensionless"),
    }

    return VariableNamespace() | _variables


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
            DottedVariableName("tweezer_power"): 1.0,
            DottedVariableName("imaging.tweezer_power"): 0.3,
            DottedVariableName("kill.tweezer_power"): 0.05,
            DottedVariableName("mot_loading.current"): 1.5 * ureg.A,
            DottedVariableName("red_mot.current"): 0.5 * ureg.A,
        }
    )
    return variables

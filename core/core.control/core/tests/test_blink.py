import logging
from pathlib import Path

import pytest

from experiment.configuration import ExperimentConfig
from experiment_control.compute_device_parameters import compute_shot_parameters
from sequence.configuration import SequenceConfig
from sequencer.channel import ChannelPattern, Concatenate, Repeat
from sequencer.instructions import (
    SequencerInstructionOld,
    ChannelLabel,
    SequencerPattern,
)
from units import Quantity
from variable.namespace import VariableNamespace

from .output import blink_instruction, channel_label, sequence

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


@pytest.fixture
def variables():
    _variables = {
        "blink_duration": Quantity(30, "millisecond"),
        "blink_period": Quantity(150, "nanosecond"),
        "red_frequency": Quantity(-9.18, "megahertz"),
        "z_current": Quantity(-3, "ampere"),
        "red_power": Quantity(-30, "decibel"),
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
def sequence_config() -> SequenceConfig:
    path = Path(__file__).parent / "blink_sequence_config.yaml"
    with open(path, "r") as file:
        config = SequenceConfig.from_yaml(file.read())
    return config


@pytest.fixture
def experiment_config() -> ExperimentConfig:
    path = Path(__file__).parent / "blink_experiment_config.yaml"
    with open(path, "r") as file:
        config = ExperimentConfig.from_yaml(file.read())
    return config


@pytest.mark.skip
def test_compile_blink(
    sequence_config: SequenceConfig,
    experiment_config: ExperimentConfig,
    variables: VariableNamespace,
):
    sequence.add_channel_instruction(channel_label, blink_instruction)
    # parameters = compute_shot_parameters(
    #     experiment_config, sequence_config.shot_configurations["shot"], variables
    # )


@pytest.mark.skip
def test_blink():
    sequencer = SequencerInstructionOld.from_channel_instruction(
        ChannelLabel(0), ChannelPattern((True,)) * 166667
    )

    blink = Concatenate(
        (
            Repeat(
                Concatenate(
                    (
                        Repeat(ChannelPattern((True,)), 8),
                        Repeat(ChannelPattern((False,)), 8),
                    )
                ),
                10416,
            ),
            Repeat(ChannelPattern((False,)), 11),
        )
    )

    sequencer.add_channel_instruction(ChannelLabel(1), blink)

import logging
from collections.abc import Iterable
from functools import singledispatch
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from experiment.configuration import ExperimentConfig
from experiment_control.compute_device_parameters import (
    compile_step_durations,
    compute_shot_parameters,
    get_step_bounds,
)
from sequence.configuration import SequenceConfig
from sequencer.channel import ChannelInstruction, ChannelPattern, Repeat, Concatenate
from units import Quantity
from variable.name import DottedVariableName
from variable.namespace import VariableNamespace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

with open(Path(__file__).parent / "debug_experiment_config.yaml") as f:
    experiment_config_2 = ExperimentConfig.from_yaml(f.read())

with open(Path(__file__).parent / "debug_sequence_config.yaml") as f:
    sequence_config_2 = SequenceConfig.from_yaml(f.read())

v = {
    "ramp_time": Quantity(80, "millisecond"),
    "mot_loading.red.power": Quantity(0, "decibel"),
    "mot_loading.red.frequency": Quantity(-3.2, "megahertz"),
    "mot_loading.current": Quantity(3.6, "ampere"),
    "mot_loading.blue.power": Quantity(1.0, "dimensionless"),
    "mot_loading.blue.frequency": Quantity(19, "megahertz"),
    "mot_loading.x_current": Quantity(0.47, "ampere"),
    "mot_loading.y_current": Quantity(0, "ampere"),
    "mot_loading.z_current": Quantity(0.3, "ampere"),
    "red_mot.x_current": Quantity(0.25, "ampere"),
    "red_mot.y_current": Quantity(0.14, "ampere"),
    "red_mot.z_current": Quantity(-0.12, "ampere"),
    "red_mot.frequency": Quantity(-1.29, "megahertz"),
    "red_mot.power": Quantity(-36, "decibel"),
    "red_mot.current": Quantity(1, "ampere"),
    "push_power": Quantity(0.5, "milliwatt"),
    "exposure": Quantity(30, "millisecond"),
    "imaging.x_current": Quantity(0.25, "ampere"),
    "imaging.y_current": Quantity(4.94, "ampere"),
    "imaging.z_current": Quantity(0.183, "ampere"),
    "imaging.power": Quantity(-25, "decibel"),
    "imaging.frequency": Quantity(-18.03, "megahertz"),
    "imaging.tweezer_power": Quantity(0.4, "dimensionless"),
    "hwp_angle": Quantity(137.5, "dimensionless"),
    "tweezer_power": Quantity(1.0, "dimensionless"),
    "kill.tweezer_power": Quantity(0.05, "dimensionless"),
    "kill.blue.frequency": Quantity(30, "megahertz"),
    "kill_duration": Quantity(1.5, "microsecond"),
    "rep": Quantity(0, "dimensionless"),
}

v = {DottedVariableName(k): v for k, v in v.items()}

variables_2 = VariableNamespace()
variables_2.update(v)


def test_compile_analog_lane() -> None:
    shot_config = sequence_config_2.shot_configurations["shot"]
    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables_2,
    )

    parameters = compute_shot_parameters(
        experiment_config_2, sequence_config_2.shot_configurations["shot"], variables_2
    )

    instruction = parameters["Spincore PulseBlaster sequencer"]["sequence"][0]
    flattened = instruction.flatten().values.astype(int)
    number_rise = np.sum(np.maximum(flattened[:-1] - flattened[1:], 0))
    logger.debug(f"{number_rise=}")
    logger.debug(instruction.compact_length_repr())
    logger.debug(f"{len(instruction)=}")
    # plot_instruction(instruction, durations, 50e-9)
    # plot_instruction_band(instruction, 50e-9, vertical_offset=0)
    # plot_steps(durations)

    instruction = parameters["NI6738 card"]["sequence"][12]

    logger.debug(f"{len(instruction)=}")

    # plot_instruction_band(instruction, 3e-6, vertical_offset=1)
    # plot_instruction(instruction, durations, 3e-6)
    # plt.xlim(0.331 - 10e-6, 0.331 + 10e-6)

    # plt.show()

    logger.debug(instruction.compact_length_repr())

    assert number_rise == number_changes(instruction)


@singledispatch
def number_changes(instruction: ChannelInstruction) -> int:
    raise NotImplementedError(f"Cannot compute number of changes for {instruction}")


@number_changes.register
def _(instruction: ChannelPattern) -> int:
    return len(instruction)


@number_changes.register
def _(instruction: Concatenate) -> int:
    return sum(
        number_changes(sub_instruction) for sub_instruction in instruction.instructions
    )


@number_changes.register
def _(instruction: Repeat) -> int:
    return 1


def plot_instruction_band(
    instruction: ChannelInstruction, multiplier, vertical_offset
) -> None:
    _plot_instruction_band(instruction, 0, multiplier, vertical_offset)


@singledispatch
def _plot_instruction_band(
    instruction: ChannelInstruction, offset: int, multiplier, vertical_offset
) -> None:
    raise NotImplementedError(f"Cannot plot instruction {instruction}")


@_plot_instruction_band.register
def _(instruction: ChannelPattern, offset: int, multiplier, vertical_offset) -> None:
    plt.fill_between(
        [offset * multiplier, (offset + len(instruction)) * multiplier],
        vertical_offset,
        vertical_offset + 1,
    )


@_plot_instruction_band.register
def _(instruction: Concatenate, offset: int, multiplier, vertical_offset) -> None:
    offset = offset
    for sub_instruction in instruction.instructions:
        _plot_instruction_band(sub_instruction, offset, multiplier, vertical_offset)
        offset += len(sub_instruction)


@_plot_instruction_band.register
def _(instruction: Repeat, offset: int, multiplier, vertical_offset) -> None:
    offset = offset
    plt.fill_between(
        x=[
            offset * multiplier,
            (offset + len(instruction.instruction) * instruction.number_repetitions)
            * multiplier,
        ],
        y1=vertical_offset,
        y2=vertical_offset + 1,
    )


def plot_instruction(
    instruction: ChannelInstruction,
    step_durations: Iterable[float],
    time_step: float,
) -> None:
    values = instruction.flatten().values
    times = np.arange(len(values)) * time_step
    plt.plot(times, values, "-o", drawstyle="steps-post", color="k")


def plot_steps(
    step_durations: Iterable[float],
) -> None:
    step_bounds = get_step_bounds(step_durations)
    for step, step_bound in enumerate(step_bounds):
        plt.axvline(step_bound, ls="--", color="k")
        plt.text(x=step_bound, y=0.5, s=f"{step}")


# test_compile_analog_lane()


instruction = Concatenate(
    (
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((False,)), 199950),
        Repeat(
            Concatenate(
                (
                    Repeat(ChannelPattern((True,)), 25),
                    Repeat(ChannelPattern((False,)), 25),
                )
            ),
            32000,
        ),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((False,)), 2999950),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((False,)), 19950),
        Repeat(
            Concatenate(
                (
                    Repeat(ChannelPattern((True,)), 25),
                    Repeat(ChannelPattern((False,)), 25),
                )
            ),
            12000,
        ),
        Repeat(
            Concatenate(
                (
                    Repeat(ChannelPattern((True,)), 25),
                    Repeat(ChannelPattern((False,)), 25),
                )
            ),
            4000,
        ),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((False,)), 199950),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((False,)), 599951),
        Repeat(ChannelPattern((False,)), 49),
        Repeat(
            Concatenate(
                (
                    Repeat(ChannelPattern((True,)), 25),
                    Repeat(ChannelPattern((False,)), 25),
                )
            ),
            3199,
        ),
        ChannelPattern((True,)),
        Repeat(ChannelPattern((True,)), 2),
        Repeat(ChannelPattern((True,)), 2),
        Repeat(ChannelPattern((True,)), 9),
        Repeat(ChannelPattern((True,)), 11),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(
            Concatenate(
                (
                    Repeat(ChannelPattern((True,)), 25),
                    Repeat(ChannelPattern((False,)), 25),
                )
            ),
            1996,
        ),
        Repeat(ChannelPattern((True,)), 14),
        Repeat(ChannelPattern((True,)), 11),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(
            Concatenate(
                (
                    Repeat(ChannelPattern((True,)), 25),
                    Repeat(ChannelPattern((False,)), 25),
                )
            ),
            3,
        ),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((False,)), 599764),
        Repeat(ChannelPattern((False,)), 186),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((False,)), 19764),
        Repeat(ChannelPattern((False,)), 186),
        Repeat(ChannelPattern((True,)), 25),
        Repeat(ChannelPattern((False,)), 25),
        Repeat(ChannelPattern((False,)), 199764),
    )
)

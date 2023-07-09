from collections.abc import Iterable

import matplotlib.pyplot as plt
import numpy as np

from experiment_control.compute_device_parameters import (
    compile_step_durations,
    compile_analog_lane,
    get_step_bounds,
)
from sequence.configuration import ShotConfiguration, AnalogLane
from sequencer.channel import ChannelInstruction
from variable.namespace import VariableNamespace


def test_compile_analog_lane(
    shot_config: ShotConfiguration, variables: VariableNamespace
) -> None:
    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables,
    )

    time_step = .5e-6

    lane = shot_config.find_lane("Tweezers power (AOM)")
    assert isinstance(lane, AnalogLane)
    instruction = compile_analog_lane(
        shot_config.step_names, durations, lane, variables, time_step
    )
    plot_instruction(instruction, durations, time_step)


def plot_instruction(
    instruction: ChannelInstruction[float],
    step_durations: Iterable[float],
    time_step: float,
) -> None:
    values = instruction.flatten().values
    times = np.arange(len(values)) * time_step
    plt.plot(times, values, ".", drawstyle="steps-post")
    step_bounds = get_step_bounds(step_durations)
    for step_bound in step_bounds:
        plt.axvline(step_bound, ls="--", color="k")
    plt.show()

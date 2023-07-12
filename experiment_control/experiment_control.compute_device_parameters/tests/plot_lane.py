from collections.abc import Iterable
from numbers import Real

import matplotlib.pyplot as plt
import numpy as np

from experiment_control.compute_device_parameters import (
    compile_step_durations,
    compile_analog_lane,
    get_step_bounds,
)
from sequence.configuration import ShotConfiguration, AnalogLane
from sequencer.channel import ChannelInstruction, ChannelPattern, Repeat, Concatenate
from variable.namespace import VariableNamespace


def test_compile_analog_lane(
    shot_config: ShotConfiguration, variables: VariableNamespace
) -> None:
    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables,
    )

    time_step = 50
    #
    # lane = shot_config.find_lane("Tweezers power (AOM)")
    # assert isinstance(lane, AnalogLane)
    # instruction = compile_analog_lane(
    #     shot_config.step_names, durations, lane, variables, time_step
    # )
    plot_instruction(instruction, durations, time_step)


def plot_instruction(
    instruction: ChannelInstruction,
    # step_durations: Iterable[float],
    time_step: float,
) -> None:
    values = instruction.flatten().values
    times = np.arange(len(values)) * time_step
    plt.plot(times, values, drawstyle="steps-post")
    # step_bounds = get_step_bounds(step_durations)
    # for step_bound in step_bounds:
    #     plt.axvline(step_bound, ls="--", color="k")
    plt.show()

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
plot_instruction(instruction, 50)

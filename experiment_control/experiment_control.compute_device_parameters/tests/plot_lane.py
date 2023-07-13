from collections.abc import Iterable

import matplotlib.pyplot as plt
import numpy as np

from experiment.configuration import ExperimentConfig
from experiment_control.compute_device_parameters import (
    compile_step_durations,
    compute_shot_parameters, get_step_bounds,
)
from sequence.configuration import SequenceConfig
from sequencer.channel import ChannelInstruction, ChannelPattern, Repeat, Concatenate
from variable.namespace import VariableNamespace


def test_compile_analog_lane(
    experiment_config_2: ExperimentConfig,
    sequence_config_2: SequenceConfig,
    variables_2: VariableNamespace,
) -> None:
    shot_config = sequence_config_2.shot_configurations["shot"]
    durations = compile_step_durations(
        step_durations=shot_config.step_durations,
        step_names=shot_config.step_names,
        variables=variables_2,
    )

    parameters = compute_shot_parameters(
        experiment_config_2, sequence_config_2.shot_configurations["shot"], variables_2
    )

    cam_trig = parameters["NI6738 card"]["sequence"][0]
    #
    # lane = shot_config.find_lane("Tweezers power (AOM)")
    # assert isinstance(lane, AnalogLane)
    # instruction = compile_analog_lane(
    #     shot_config.step_names, durations, lane, variables, time_step
    # )
    plot_instruction(cam_trig, durations, 2.5e-6)


def plot_instruction(
    instruction: ChannelInstruction,
    step_durations: Iterable[float],
    time_step: float,
) -> None:
    values = instruction.flatten().values
    times = np.arange(len(values)) * time_step
    plt.plot(times, values, drawstyle="steps-post")
    step_bounds = get_step_bounds(step_durations)
    for step_bound in step_bounds:
        plt.axvline(step_bound, ls="--", color="k", zorder=-1)
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

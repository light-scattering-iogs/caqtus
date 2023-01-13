import logging

import numpy as np

from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    ChannelSettings,
    StepConfiguration,
    StepChangeCondition,
)
from trap_signal_generator.configuration import StaticTrapConfiguration
from trap_signal_generator.runtime import StaticTrapGenerator, MovingTrapGenerator


logging.basicConfig()

with open("./config_x.yaml", "r") as f:
    config_x = StaticTrapConfiguration.from_yaml(f.read())


amplitude_one_tone = 0.135
scale_x = np.sqrt(config_x.number_tones) * amplitude_one_tone
scale_y = amplitude_one_tone


def generate_filled_traps(N):
    return np.arange(N)[np.random.binomial(1, 0.5, N) == 1]


filled_traps = generate_filled_traps(config_x.number_tones)

starting_frequencies = np.array(config_x.frequencies)[filled_traps]
starting_phases = (
    2 * np.pi * starting_frequencies * config_x.number_samples / config_x.sampling_rate
    + np.array(config_x.phases)[filled_traps]
)
amplitudes = np.array(config_x.amplitudes)[filled_traps]

target_frequencies = config_x.frequencies[: len(filled_traps)]
target_phases = config_x.phases[: len(filled_traps)]

moving_generator = MovingTrapGenerator(
    starting_frequencies=starting_frequencies,
    target_frequencies=target_frequencies,
    starting_phases=starting_phases,
    target_phases=target_phases,
    amplitudes=amplitudes,
    sampling_rate=config_x.sampling_rate,
    number_samples=config_x.number_samples,
    trajectory_function="sin",
)

target_generator = StaticTrapGenerator(
    frequencies=target_frequencies,
    amplitudes=amplitudes,
    phases=target_phases,
    sampling_rate=config_x.sampling_rate,
    number_samples=config_x.number_samples,
)

y_scan_generator = MovingTrapGenerator(
    starting_frequencies=[80e6],
    target_frequencies=[70e6],
    starting_phases=[0],
    target_phases=[0],
    amplitudes=[2**15],
    number_samples=config_x.number_samples * 3,
    sampling_rate=config_x.sampling_rate,
    trajectory_function="linear",
)

data_y = y_scan_generator.compute_signal()

static_trap_generator_x = StaticTrapGenerator.from_configuration(config_x)

with SpectrumAWGM4i66xxX8(
    name="AWG",
    board_id="/dev/spcm0",
    channel_settings=(
        ChannelSettings(name="X", enabled=True, amplitude=scale_x, maximum_power=-7),
        ChannelSettings(name="Y", enabled=True, amplitude=scale_y, maximum_power=-7),
    ),
    segment_names=frozenset(["all_static_traps", "moving_traps", "target_traps"]),
    steps={
        "all_static_traps": StepConfiguration(
            segment="all_static_traps",
            next_step="moving_traps",
            repetition=1,
            change_condition=StepChangeCondition.ALWAYS,
        ),
        "moving_traps": StepConfiguration(
            segment="moving_traps",
            next_step="target_traps",
            repetition=1,
            change_condition=StepChangeCondition.ALWAYS,
        ),
        "target_traps": StepConfiguration(
            segment="target_traps",
            next_step="all_static_traps",
            repetition=1,
            change_condition=StepChangeCondition.ALWAYS,
        ),
    },
    first_step="all_static_traps",
    sampling_rate=static_trap_generator_x.sampling_rate,
) as awg:
    data = np.int16(
        (
            static_trap_generator_x.compute_signal(),
            data_y[: config_x.number_samples],
        )
    )

    awg.write_segment_data("all_static_traps", data)

    y_scan_generator.starting_frequencies = [75e6]
    y_scan_generator.target_frequencies = [70e6]

    data = np.int16(
        (
            moving_generator.compute_signal(),
            data_y[config_x.number_samples : 2 * config_x.number_samples],
        )
    )

    awg.write_segment_data("moving_traps", data)

    y_scan_generator.starting_frequencies = [70e6]
    y_scan_generator.target_frequencies = [65e6]
    data = np.int16(
        (
            target_generator.compute_signal(),
            data_y[2 * config_x.number_samples :],
        )
    )
    awg.write_segment_data("target_traps", data)

    awg.run()
    input()
    awg.stop()

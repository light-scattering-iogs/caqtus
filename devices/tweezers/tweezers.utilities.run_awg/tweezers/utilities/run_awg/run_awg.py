import logging

import numpy as np

from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    ChannelSettings,
    StepConfiguration,
    StepChangeCondition,
)
from trap_signal_generator.configuration import StaticTrapConfiguration
from trap_signal_generator.runtime import StaticTrapGenerator

logging.basicConfig()

with open("./config_x.yaml", "r") as f:
    config_x = StaticTrapConfiguration.from_yaml(f.read())

with open("./config_y.yaml", "r") as f:
    config_y = StaticTrapConfiguration.from_yaml(f.read())

amplitude_one_tone = 0.135
scale_x = np.sqrt(config_x.number_tones) * amplitude_one_tone
scale_y = np.sqrt(config_y.number_tones) * amplitude_one_tone

assert config_x.number_samples == config_y.number_samples
assert config_x.sampling_rate == config_y.sampling_rate

static_trap_generator_x = StaticTrapGenerator.from_configuration(config_x)
static_trap_generator_y = StaticTrapGenerator.from_configuration(config_y)

with SpectrumAWGM4i66xxX8(
    name="AWG",
    board_id="/dev/spcm0",
    channel_settings=(
        ChannelSettings(name="X", enabled=True, amplitude=scale_x, maximum_power=-6),
        ChannelSettings(name="Y", enabled=True, amplitude=scale_y, maximum_power=-6),
    ),
    segment_names=frozenset(["segment_0", "segment_1"]),
    steps={
        "step_0": StepConfiguration(
            segment="segment_0",
            next_step="step_0",
            repetition=1,
            change_condition=StepChangeCondition.ALWAYS,
        ),
        "step_1": StepConfiguration(
            segment="segment_1",
            next_step="step_0",
            repetition=100,
            change_condition=StepChangeCondition.ALWAYS,
        ),
    },
    first_step="step_0",
    sampling_rate=static_trap_generator_x.sampling_rate,
) as awg:
    data_0 = np.int16(
        (
            static_trap_generator_x.compute_signal(),
            static_trap_generator_y.compute_signal(),
        )
    )
    static_trap_generator_y.frequencies = (
        np.array(static_trap_generator_y.frequencies) + 4e6
    )
    data_1 = np.int16(
        (
            static_trap_generator_x.compute_signal(),
            static_trap_generator_y.compute_signal(),
        )
    )

    awg.write_segment_data("segment_0", data_0)
    awg.write_segment_data("segment_1", data_1)
    awg.run()
    input()
    awg.stop()

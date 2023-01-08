import logging
from trap_signal_generator.configuration import StaticTrapConfiguration
from trap_signal_generator.runtime import StaticTrapGenerator

import numpy as np

from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    ChannelSettings,
    Segment,
)

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
        ChannelSettings(name="X", enabled=True, amplitude=scale_x, maximum_power=-7),
        ChannelSettings(name="Y", enabled=True, amplitude=scale_y, maximum_power=-7),
    ),
    segment_names={"segment_1"},
    first_step=0,
    sampling_rate=static_trap_generator_x.sampling_rate,
) as awg:
    data = np.int16(
        (
            static_trap_generator_x.compute_signal(),
            static_trap_generator_y.compute_signal(),
        )
    )
    awg.write_segment_data("segment_1", data)
    awg.run()
    input()
    awg.stop()

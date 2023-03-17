import numpy as np

from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    ChannelSettings,
    StepConfiguration,
    StepChangeCondition,
)


def initialize_awg(config_x, config_y):

    amplitude_one_tone = 0.135
    sample_rate = config_x.sampling_rate
    scale_x = np.sqrt(config_x.number_tones) * amplitude_one_tone
    scale_y = np.sqrt(config_y.number_tones) * amplitude_one_tone

    AWG = SpectrumAWGM4i66xxX8(
        name="AWG",
        board_id="/dev/spcm0",
        channel_settings=(
            ChannelSettings(name="X", enabled=True, amplitude=scale_x, maximum_power=-7),
            ChannelSettings(name="Y", enabled=True, amplitude=scale_y, maximum_power=-7),
        ),
        segment_names=frozenset(["segment_0"]),
        steps={
            "step_0": StepConfiguration(
                segment="segment_0",
                next_step="step_0",
                repetition=1,
                change_condition=StepChangeCondition.ALWAYS,
            ),

        },
        first_step="step_0",
        sampling_rate=sample_rate,
    )
    return AWG

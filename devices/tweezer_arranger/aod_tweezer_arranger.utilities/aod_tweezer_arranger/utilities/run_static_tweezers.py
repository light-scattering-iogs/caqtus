import logging

import numpy as np

from aod_tweezer_arranger.configuration import (
    AODTweezerConfiguration,
    AODTweezerArrangerConfiguration,
)
from aod_tweezer_arranger.runtime import SignalGenerator
from device.name import DeviceName
from experiment.session import get_standard_experiment_session
from spectum_awg_m4i66xx_x8.configuration import ChannelSettings
from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    StepConfiguration,
    StepChangeCondition,
    StepName,
    SegmentName,
)

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")
logging.basicConfig()

DEVICE_NAME = DeviceName("Tweezer arranger")
TWEEZER_CONFIG_NAME = "5x5 tweezers"


def main():
    session = get_standard_experiment_session()
    with session.activate():
        experiment_config = session.get_current_experiment_config()
        arranger_config: AODTweezerArrangerConfiguration = (
            experiment_config.get_device_config(DEVICE_NAME)
        )
        tweezer_config = arranger_config[TWEEZER_CONFIG_NAME]

    awg = initialize_awg(tweezer_config)

    with awg:
        write_config_to_awg(awg, tweezer_config)
        awg.start_sequence()
        input()
        awg.stop_sequence()


def initialize_awg(tweezer_config: AODTweezerConfiguration) -> SpectrumAWGM4i66xxX8:
    awg = SpectrumAWGM4i66xxX8(
        name="AWG",
        board_id="/dev/spcm0",
        channel_settings=(
            ChannelSettings(
                name="X",
                enabled=True,
                amplitude=tweezer_config.scale_x,
                maximum_power=-4,
            ),
            ChannelSettings(
                name="Y",
                enabled=True,
                amplitude=tweezer_config.scale_y,
                maximum_power=-4,
            ),
        ),
        segment_names={SegmentName("segment_0")},
        steps={
            StepName("step_0"): StepConfiguration(
                segment=SegmentName("segment_0"),
                next_step=StepName("step_0"),
                repetition=1,
                change_condition=StepChangeCondition.ALWAYS,
            ),
        },
        first_step=StepName("step_0"),
        sampling_rate=int(tweezer_config.sampling_rate),
    )
    return awg


def write_config_to_awg(
    awg: SpectrumAWGM4i66xxX8, tweezer_config: AODTweezerConfiguration
):
    with SignalGenerator(tweezer_config.sampling_rate) as signal_generator:
        data = np.array(
            (
                signal_generator.generate_signal_static_traps(
                    amplitudes=tweezer_config.amplitudes_x,
                    frequencies=tweezer_config.frequencies_x,
                    phases=tweezer_config.phases_x,
                    number_samples=tweezer_config.number_samples,
                ),
                signal_generator.generate_signal_static_traps(
                    amplitudes=tweezer_config.amplitudes_y,
                    frequencies=tweezer_config.frequencies_y,
                    phases=tweezer_config.phases_y,
                    number_samples=tweezer_config.number_samples,
                ),
            ),
            dtype=np.int16,
        )
        awg.update_parameters(segment_data={SegmentName("segment_0"): data})


if __name__ == "__main__":
    main()

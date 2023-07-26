import argparse
import logging
import math
from pathlib import Path

from pre_scripted_move import MoveConfiguration, generate_move
from spectum_awg_m4i66xx_x8.configuration import ChannelSettings
from spectum_awg_m4i66xx_x8.runtime import SpectrumAWGM4i66xxX8, StepName

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig()


def main():
    parser = argparse.ArgumentParser(description="Run a pre-scripted move on the AWG.")
    parser.add_argument(
        "-i", "--input", help="Path to the move configuration", type=Path
    )

    args = parser.parse_args()
    input_file = args.input

    with open(input_file, "r") as f:
        move_config = MoveConfiguration.from_yaml(f.read())

    steps, segments = generate_move(move_config)

    amplitude_one_tone = 0.165
    scale_x = math.sqrt(move_config.number_tone_x) * amplitude_one_tone
    scale_y = math.sqrt(move_config.number_tone_y) * amplitude_one_tone
    awg = SpectrumAWGM4i66xxX8(
        name="AWG",
        board_id="/dev/spcm0",
        channel_settings=(
            ChannelSettings(
                name="X", enabled=True, amplitude=scale_x, maximum_power=-4
            ),
            ChannelSettings(
                name="Y", enabled=True, amplitude=scale_y, maximum_power=-4
            ),
        ),
        segment_names=set(segments),
        steps=steps,
        first_step=StepName("initial"),
        sampling_rate=int(move_config.sampling_rate),
    )

    with awg:
        awg.update_parameters(segment_data=segments)
        awg.run()
        input()
        awg.stop_sequence()


if __name__ == "__main__":
    main()

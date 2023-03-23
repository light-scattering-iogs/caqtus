import copy
import logging

import numpy as np

from analyze_spots import GridSpotIntensitiesMeasurer
from pixelfly import PixelflyBoard, Mode, BinMode, PixelDepth
from spectum_awg_m4i66xx_x8.configuration import ChannelSettings
from spectum_awg_m4i66xx_x8.runtime import (
    SpectrumAWGM4i66xxX8,
    StepConfiguration,
    StepChangeCondition,
)
from trap_signal_generator.runtime import StaticTrapGenerator

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")
logging.basicConfig()

BETA = 0.1
NUMBER_ITERATIONS = 25
ROI_RADIUS = 30
TRAP_RELATIVE_THRESHOLD = 0.3


pixelfly = PixelflyBoard(
    name="pixelfly",
    board_number=0,
    mode=Mode.SW_TRIGGER | Mode.ASYNC_SHUTTER,
    exp_time=15,  # in µs
    hbin=BinMode.BIN_1X,
    vbin=BinMode.BIN_1X,
    gain=False,
    bit_pix=PixelDepth.BITS_12,
)


def acquire_picture():
    with pixelfly:
        pixelfly.start_acquisition()
        picture = pixelfly.read_image(1000).astype(float)
        pixelfly.stop_acquisition()
    return picture


def initialize_awg(sampling_rate: float, number_tones_x: int, number_tones_y: int):
    amplitude_one_tone = 0.135
    scale_x = number_tones_x**0.5 * amplitude_one_tone
    scale_y = number_tones_y**0.5 * amplitude_one_tone

    awg = SpectrumAWGM4i66xxX8(
        name="AWG",
        board_id="/dev/spcm0",
        channel_settings=(
            ChannelSettings(
                name="X", enabled=True, amplitude=scale_x, maximum_power=-7
            ),
            ChannelSettings(
                name="Y", enabled=True, amplitude=scale_y, maximum_power=-7
            ),
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
        sampling_rate=int(sampling_rate),
    )
    return awg


def homogenize(
    initial_signal_generator_x: StaticTrapGenerator,
    initial_signal_generator_y: StaticTrapGenerator,
):
    signal_generator_x = copy.deepcopy(initial_signal_generator_x)
    signal_generator_y = copy.deepcopy(initial_signal_generator_y)

    awg = initialize_awg(
        signal_generator_x.sampling_rate,
        signal_generator_x.number_tones,
        signal_generator_y.number_tones,
    )

    with awg:
        awg.stop()
    background_picture = acquire_picture()

    with awg:
        data = np.int16(
            (
                signal_generator_x.compute_signal(),
                signal_generator_y.compute_signal(),
            )
        )
        awg.write_segment_data("segment_0", data)
        awg.run()
        picture = acquire_picture() - background_picture

    spot_analyzer = GridSpotIntensitiesMeasurer(
        number_rows=signal_generator_x.number_tones,
        number_columns=signal_generator_y.number_tones,
    )
    spot_analyzer.register_regions_of_interest(
        picture, relative_threshold=TRAP_RELATIVE_THRESHOLD, radius=ROI_RADIUS
    )

    intensities = []
    amplitudes_x = []
    amplitudes_y = []
    for repetition in range(NUMBER_ITERATIONS):
        with awg:
            data = np.int16(
                (
                    signal_generator_x.compute_signal(),
                    signal_generator_y.compute_signal(),
                )
            )
            awg.write_segment_data("segment_0", data)
            awg.run()
            picture = acquire_picture() - background_picture

        intensity_matrix = spot_analyzer.compute_intensity(picture, method=np.sum)
        intensities.append(intensity_matrix)

        error = np.std(intensity_matrix) / np.mean(intensity_matrix)
        logger.info(f"std/mean = {error * 1e2:.2f}%")

        # Beware how to flip the intensity matrix depending on the imaging setup
        new_row_amplitudes, new_column_amplitudes = compute_new_amplitudes(
            intensity_matrix[::, ::-1],
            BETA,
            np.array(signal_generator_x.amplitudes),
            np.array(signal_generator_y.amplitudes),
        )

        signal_generator_x.amplitudes = new_row_amplitudes
        signal_generator_y.amplitudes = new_column_amplitudes

        amplitudes_x.append(signal_generator_x.amplitudes)
        amplitudes_y.append(signal_generator_y.amplitudes)

    return intensities, amplitudes_x, amplitudes_y


def compute_new_amplitudes(
    intensity_matrix: np.ndarray,
    beta: float,
    amplitude_rows: np.ndarray,
    amplitude_columns: np.ndarray,
):
    row_intensities = np.mean(intensity_matrix, axis=1)
    column_intensities = np.mean(intensity_matrix, axis=0)

    relative_row_intensities = row_intensities / np.sum(row_intensities)
    relative_column_intensities = column_intensities / np.sum(column_intensities)

    # Here we need a function that is higher than 1 when the relative intensity is lower than 1 and lower than 1 when
    # the relative intensity is higher than 1. The beta parameter controls the steepness of the function and a low value
    # (0.1~0.5) prevents oscillations.
    row_gains = 1 / relative_row_intensities**beta
    column_gains = 1 / relative_column_intensities**beta

    new_row_amplitudes = row_gains * amplitude_rows
    new_column_amplitudes = column_gains * amplitude_columns

    # This is a renormalization step to keep the total RF power constant
    new_row_amplitudes *= (
        np.sum(amplitude_rows**2) / np.sum(new_row_amplitudes**2)
    ) ** 0.5
    new_column_amplitudes *= (
        np.sum(amplitude_columns**2) / np.sum(new_column_amplitudes**2)
    ) ** 0.5

    return new_row_amplitudes, new_column_amplitudes

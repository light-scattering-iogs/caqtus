import copy
import logging
import time
from typing import Optional

import numpy as np

from analyze_spots import GridSpotAnalyzer
from aod_tweezer_arranger.configuration import AODTweezerConfiguration
from device.name import DeviceName
from pixelfly.runtime import PixelflyBoard, Mode, BinMode, PixelDepth
from run_static_tweezers import initialize_awg, write_config_to_awg

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


def homogenize(
        initial_tweezer_configuration: AODTweezerConfiguration,
        exposure: int = 30,
        roi_radius: float = 20,
        beta=0.3,
        number_iterations=25,
        relative_threshold=0.2,
        weight_matrix: Optional[np.ndarray] = None,
):
    """Attempts to homogenize the trap by adjusting the AWG power in each tone.

    This function execute a loop in which, at, each step, it takes a picture, measure the intensity of the spots and
    then feedback on the AWG power to try to homogenize the trap.

    Args:
        initial_tweezer_configuration: contains the initial values to generate the AWG signal
        exposure: exposure time in µs for the camera
        roi_radius: radius of the region of interest in pixels around each trap
        beta: feedback coefficient, the higher, the more aggressive the feedback, typically between 0.1 and 0.5
        number_iterations: number of iterations to perform before stopping the homogenization
        relative_threshold: threshold to detect the spots in the picture
    """
    if weight_matrix is None:
        weight_matrix = np.ones(
            (
                initial_tweezer_configuration.number_tweezers_along_x,
                initial_tweezer_configuration.number_tweezers_along_y,
            )
        )

    pixelfly = PixelflyBoard(
        name=DeviceName("pixelfly"),
        board_number=0,
        mode=Mode.SW_TRIGGER | Mode.ASYNC_SHUTTER,
        exp_time=exposure,  # in µs
        hbin=BinMode.BIN_1X,
        vbin=BinMode.BIN_1X,
        gain=False,
        bit_pix=PixelDepth.BITS_12,
    )

    awg = initialize_awg(initial_tweezer_configuration)
    tweezer_configuration = copy.deepcopy(initial_tweezer_configuration)

    with awg:
        awg.stop()

    background_picture = acquire_picture(pixelfly)

    with awg:
        write_config_to_awg(awg, tweezer_configuration)
        awg.run()
        picture = acquire_picture(pixelfly) - background_picture

    spot_analyzer = GridSpotAnalyzer(
        number_rows=tweezer_configuration.number_tweezers_along_y,
        number_columns=tweezer_configuration.number_tweezers_along_x,
    )
    spot_analyzer.register_regions_of_interest(
        picture, relative_threshold=relative_threshold, radius=roi_radius
    )

    intensities = []
    amplitudes_x = []
    amplitudes_y = []
    for repetition in range(number_iterations):
        with awg:
            write_config_to_awg(awg, tweezer_configuration)
            awg.run()
            time.sleep(0.05)
            picture = acquire_picture(pixelfly) - background_picture

        intensity_matrix = spot_analyzer.compute_intensity_matrix(
            picture, method=np.sum
        )
        intensities.append(intensity_matrix)

        error = np.std(intensity_matrix) / np.mean(intensity_matrix)
        logger.info(f"std/mean = {error * 1e2:.2f}%")

        # Beware how to flip the intensity matrix depending on the imaging setup
        new_row_amplitudes, new_column_amplitudes = compute_new_amplitudes(
            intensity_matrix[::-1, ::] * weight_matrix,
            beta,
            np.array(tweezer_configuration.amplitudes_x),
            np.array(tweezer_configuration.amplitudes_y),
        )

        tweezer_configuration.amplitudes_x = tuple(new_row_amplitudes)
        tweezer_configuration.amplitudes_y = tuple(new_column_amplitudes)

        amplitudes_x.append(tweezer_configuration.amplitudes_x)
        amplitudes_y.append(tweezer_configuration.amplitudes_y)

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
                                  np.sum(amplitude_rows ** 2) / np.sum(new_row_amplitudes ** 2)
                          ) ** 0.5
    new_column_amplitudes *= (
                                     np.sum(amplitude_columns ** 2) / np.sum(new_column_amplitudes ** 2)
                             ) ** 0.5

    return new_row_amplitudes, new_column_amplitudes


def acquire_picture(pixelfly: PixelflyBoard):
    with pixelfly:
        pixelfly.start_acquisition()
        picture = pixelfly.read_image(1000).astype(float)
        pixelfly.stop_acquisition()
    return picture

import argparse
import logging
from pathlib import Path
from warnings import warn

import numpy as np

from aod_tweezer_arranger.configuration import (
    AODTweezerConfiguration,
    AODTweezerArrangerConfiguration,
)
from device.name import DeviceName
from experiment.session import get_standard_experiment_session
from static_trap_generator import StaticTrapGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

AMPLITUDE_ONE_TONE = 0.165  # V
DEVICE_NAME = DeviceName("Tweezer arranger")
TWEEZER_CONFIG_NAME = "30x1 2.67um - top"


def main():
    # frequencies_x = np.linspace((99 - 11.239) * 1e6, 99e6, 50)
    # frequencies_y = np.linspace(70e6, 80e6, 1)

    # frequencies_x = np.linspace(95e6, 99e6, 1)
    # frequencies_y = np.linspace(70e6, (70+30)*1e6, 50)

    frequencies_x = np.linspace(81.22e6, 98.99e6, 30)
    frequencies_y = np.linspace(80e6, 80e6, 1)

    parser = argparse.ArgumentParser(
        description="Generate a configuration for a 2D static tweezer pattern."
    )
    parser.add_argument("-o", "--output", help="Output file name.", type=Path)
    parser.add_argument(
        "--number_samples", help="Number of samples.", type=int, default=19539 * 32
    )
    parser.add_argument(
        "--sampling_rate", help="Sampling rate.", type=int, default=625_000_000
    )
    args = parser.parse_args()

    number_samples = args.number_samples
    sampling_rate = args.sampling_rate
    segment_frequency = sampling_rate / number_samples

    frequencies_x = prevent_beating_in_array(frequencies_x, segment_frequency)
    frequencies_x = rounded_frequencies(frequencies_x, segment_frequency)

    frequencies_y = prevent_beating_in_array(frequencies_y, segment_frequency)
    frequencies_y = rounded_frequencies(frequencies_y, segment_frequency)

    amplitudes_x = np.ones(len(frequencies_x)) / len(frequencies_x)
    amplitudes_y = np.ones(len(frequencies_y)) / len(frequencies_y)

    config = get_trap_config(
        frequencies_x,
        amplitudes_x,
        frequencies_y,
        amplitudes_y,
        sampling_rate,
        number_samples,
    )

    session = get_standard_experiment_session()
    with session.activate():
        experiment_config = session.experiment_configs.get_current_config()
        arranger_config: AODTweezerArrangerConfiguration = (
            experiment_config.get_device_config(DEVICE_NAME)
        )  # type: ignore
        arranger_config[TWEEZER_CONFIG_NAME] = config
        experiment_config.set_device_config(DEVICE_NAME, arranger_config)
        session.experiment_configs.set_current_config(experiment_config)


def prevent_beating_in_array(
    frequencies: np.ndarray, segment_frequency: float
) -> np.ndarray:
    if len(frequencies) == 1:
        return frequencies
    spacing = (
        np.round((frequencies[1] - frequencies[0]) / segment_frequency)
        * segment_frequency
    )
    frequencies = frequencies[0] + np.arange(len(frequencies)) * spacing
    return frequencies


def rounded_frequencies(
    frequencies: np.ndarray, segment_frequency: float
) -> np.ndarray:
    frequencies = np.round(frequencies / segment_frequency) * segment_frequency
    return frequencies


def get_trap_config(
    frequencies_x: np.ndarray,
    amplitudes_x,
    frequencies_y,
    amplitudes_y,
    sampling_rate: float,
    number_samples: int,
) -> AODTweezerConfiguration:
    rng = np.random.default_rng(seed=0)
    static_trap_generator_x = StaticTrapGenerator(
        frequencies=frequencies_x,
        amplitudes=amplitudes_x,
        phases=rng.uniform(0, 2 * np.pi, len(frequencies_x)),
        sampling_rate=sampling_rate,
        number_samples=number_samples,
    )

    if (
        smallest_beating_x := static_trap_generator_x.compute_smallest_frequency_beating(
            4
        )
    ) < 100e3:
        warn(
            f"There is beating of {smallest_beating_x * 1e-3:.1f} kHz in the X channel"
        )

    static_trap_generator_x.optimize_phases()

    static_trap_generator_y = StaticTrapGenerator(
        frequencies=frequencies_y,
        amplitudes=amplitudes_y,
        phases=rng.uniform(0, 2 * np.pi, len(frequencies_y)),
        sampling_rate=sampling_rate,
        number_samples=number_samples,
    )

    if (
        smallest_beating_y := static_trap_generator_y.compute_smallest_frequency_beating(
            4
        )
    ) < 100e3:
        warn(
            f"There is beating of {smallest_beating_y * 1e-3:.1f} kHz in the Y channel"
        )

    static_trap_generator_y.optimize_phases()
    return AODTweezerConfiguration(
        frequencies_x=tuple(static_trap_generator_x.frequencies),
        phases_x=tuple(static_trap_generator_x.phases),
        amplitudes_x=tuple(static_trap_generator_x.amplitudes),
        frequencies_y=tuple(static_trap_generator_y.frequencies),
        phases_y=tuple(static_trap_generator_y.phases),
        amplitudes_y=tuple(static_trap_generator_y.amplitudes),
        sampling_rate=sampling_rate,
        number_samples=number_samples,
        scale_x=np.sqrt(static_trap_generator_x.number_tones) * AMPLITUDE_ONE_TONE,
        scale_y=np.sqrt(static_trap_generator_y.number_tones) * AMPLITUDE_ONE_TONE,
    )


if __name__ == "__main__":
    main()

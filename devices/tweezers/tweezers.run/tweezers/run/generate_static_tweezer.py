import argparse
import logging
from pathlib import Path

import numpy as np

from trap_signal_generator.configuration import (
    StaticTrapConfiguration,
    StaticTrapConfiguration2D,
)
from trap_signal_generator.runtime import StaticTrapGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def main():
    frequencies_x = np.linspace(76e6, 77.6e6, 5)
    frequencies_y = np.linspace(72e6, 73.6e6, 5)

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
    # parser.add_argument("frequencies_x", help="Frequencies in the X channel.", type=list[float])
    # parser.add_argument("frequencies_y", help="Frequencies in the Y channel.", type=list[float])
    args = parser.parse_args()

    number_samples = args.number_samples
    sampling_rate = args.sampling_rate
    segment_frequency = sampling_rate / number_samples

    frequencies_x = rounded_frequencies(frequencies_x, segment_frequency)
    frequencies_y = rounded_frequencies(frequencies_y, segment_frequency)

    amplitudes_x = np.ones(len(frequencies_x)) / len(frequencies_x) * (2**15 - 1)
    amplitudes_y = np.ones(len(frequencies_y)) / len(frequencies_y) * (2**15 - 1)

    config_x = get_trap_config(
        frequencies_x, amplitudes_x, sampling_rate, number_samples
    )
    config_y = get_trap_config(
        frequencies_y, amplitudes_y, sampling_rate, number_samples
    )
    config_2d = StaticTrapConfiguration2D(config_x=config_x, config_y=config_y)

    with open(args.output, "w") as f:
        f.write(config_2d.to_yaml())


def rounded_frequencies(
    frequencies: np.ndarray, segment_frequency: float
) -> np.ndarray:
    spacing = frequencies[1] - frequencies[0]
    spacing = np.round(spacing / segment_frequency) * segment_frequency
    frequencies = frequencies[0] + np.arange(len(frequencies)) * spacing
    frequencies = np.round(frequencies / segment_frequency) * segment_frequency
    return frequencies


def get_trap_config(
    frequencies: np.ndarray, amplitudes, sampling_rate, number_samples
) -> StaticTrapConfiguration:
    static_trap_generator = StaticTrapGenerator(
        frequencies=frequencies,
        amplitudes=amplitudes,
        phases=np.random.uniform(0, 2 * np.pi, len(frequencies)),
        sampling_rate=sampling_rate,
        number_samples=number_samples,
    )

    if (
        smallest_beating_x := static_trap_generator.compute_smallest_frequency_beating(
            4
        )
    ) < 100e3:
        logger.warning(
            f"There is beating of {smallest_beating_x*1e-3:.1f} kHz in the X channel"
        )

    static_trap_generator.optimize_phases()
    return static_trap_generator.get_configuration()


if __name__ == "__main__":
    main()

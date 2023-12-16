import itertools
from collections import Counter
from typing import Iterable, SupportsFloat, Self, Sequence

import numpy as np
from numpy.typing import ArrayLike
from settings_model import YAMLSerializable
from tweezer_arranger.configuration import TweezerConfiguration2D, TweezerLabel

from util import attrs


# Instances from this class have their attribute frozen such that the only way to modify some values is to create
# a new instance through __init__. This ensures that validation of the fields cannot be bypassed by mistake.
@attrs.frozen
class AODTweezerConfiguration(TweezerConfiguration2D):
    """Contains the information to generate a grid of trap with an AOD/AWG.

    Instances of this class are frozen and their attributes can't be changed once they are instantiated.
    If you want to create a copy of an instance with only some fields changed, use attrs.evolve.

    Fields:
        frequencies_x: The frequencies of each tone in Hz.
        phases_x: The phases of each tone in radian.
        amplitudes_x: The amplitudes of each tone. They have no dimension.
        scale_x: The value to multiply the x-signal by to get the voltage to send to the AWG. Must be in V.
        frequencies_y: The frequencies of each tone in Hz.
        phases_y: The phases of each tone in radian.
        amplitudes_y: The amplitudes of each tone. They have no dimension.
        scale_y: The value to multiply the y-signal by to get the voltage to send to the AWG. Must be in V.
        sampling_rate: The sampling rate of the AWG to generate the signal, in Hz.
        number_samples: The number of samples of the waveform. To generate a signal for longer times than
        number_samples / sampling_rate, the waveform is repeated.
    """

    frequencies_x: tuple[float, ...] = attrs.field(converter=to_tuple_of_float)
    phases_x: tuple[float, ...] = attrs.field(converter=to_tuple_of_float)
    amplitudes_x: tuple[float, ...] = attrs.field(converter=to_tuple_of_float)
    scale_x: float = attrs.field(
        converter=float,
        validator=attrs.validators.ge(0.0),
    )
    frequencies_y: tuple[float, ...] = attrs.field(converter=to_tuple_of_float)
    phases_y: tuple[float, ...] = attrs.field(converter=to_tuple_of_float)
    amplitudes_y: tuple[float, ...] = attrs.field(converter=to_tuple_of_float)
    scale_y: float = attrs.field(
        converter=float,
        validator=attrs.validators.ge(0.0),
    )

    sampling_rate: float = attrs.field(
        converter=float,
        validator=attrs.validators.ge(0.0),
    )
    number_samples: int = attrs.field(
        converter=int,
        validator=attrs.validators.ge(1),
    )

    @classmethod
    def create_with_optimized_phases(
        cls,
        frequencies_x: Sequence[float],
        amplitudes_x: Sequence[float],
        scale_x: float,
        frequencies_y: Sequence[float],
        amplitudes_y: Sequence[float],
        scale_y: float,
        sampling_rate: float,
        number_samples: int,
    ) -> Self:
        """Returns an in instance of this class with optimal phases.

        The phases are chosen using Schroeder's method to minimize the crest value of the signal envelope.
        The instance returned by this method will be checked like the one returned by create_with_checks.
        """

        period = number_samples / sampling_rate
        phases_x = schroeder_phases(
            np.array(amplitudes_x), np.array(frequencies_x), period
        )
        phases_y = schroeder_phases(
            np.array(amplitudes_y), np.array(frequencies_y), period
        )

        return cls.create_with_checks(
            frequencies_x=frequencies_x,
            phases_x=list(phases_x),
            amplitudes_x=amplitudes_x,
            scale_x=scale_x,
            frequencies_y=frequencies_y,
            phases_y=list(phases_y),
            amplitudes_y=amplitudes_y,
            scale_y=scale_y,
            sampling_rate=sampling_rate,
            number_samples=number_samples,
        )

    @classmethod
    def create_with_checks(
        cls,
        frequencies_x: Sequence[float],
        phases_x: Sequence[float],
        amplitudes_x: Sequence[float],
        scale_x: float,
        frequencies_y: Sequence[float],
        phases_y: Sequence[float],
        amplitudes_y: Sequence[float],
        scale_y: float,
        sampling_rate: float,
        number_samples: int,
    ) -> Self:
        """Returns an instance of AODTweezerConfiguration and checks that some constraints are verified.

        It is recommended to use this method to create a new instance of this class.
        It will run the following checks to ensure that the parameters passed are consistent:
            - ensure that the signals will never overflow above 1 or under -1.
            - ensure that the frequencies are multiple of the signal frequency sampling_rate / number_samples.

        The only reason to call the class constructor directly is if you know that the value you are passing are
        valid and the checks takes too long to run.
        """

        tweezer_configuration = cls(
            frequencies_x=frequencies_x,
            phases_x=phases_x,
            amplitudes_x=amplitudes_x,
            scale_x=scale_x,
            frequencies_y=frequencies_y,
            phases_y=phases_y,
            amplitudes_y=amplitudes_y,
            scale_y=scale_y,
            sampling_rate=sampling_rate,
            number_samples=number_samples,
        )
        times = np.arange(number_samples) / sampling_rate
        signal_x = compute_signal(
            times,
            tweezer_configuration.amplitudes_x,
            tweezer_configuration.frequencies_x,
            tweezer_configuration.phases_x,
        )
        if not np.all(np.logical_and(-1 <= signal_x, signal_x < 1)):
            raise ValueError("Signal along x is not in [-1, 1[")
        signal_y = compute_signal(
            times,
            tweezer_configuration.amplitudes_y,
            tweezer_configuration.frequencies_y,
            tweezer_configuration.phases_y,
        )
        if not np.all(np.logical_and(-1 <= signal_y, signal_y < 1)):
            raise ValueError("Signal along y is not in [-1, 1[")

        if not are_frequencies_multiple_of_fundamental(
            tweezer_configuration.frequencies_x, tweezer_configuration.segment_frequency
        ):
            raise ValueError(
                "The frequencies along x must be integer multiples of the segment frequency"
            )
        if not are_frequencies_multiple_of_fundamental(
            tweezer_configuration.frequencies_y, tweezer_configuration.segment_frequency
        ):
            raise ValueError(
                "The frequencies along y must be integer multiples of the segment frequency"
            )

        return tweezer_configuration

    @frequencies_x.validator  # type: ignore
    def validate_frequencies_x(self, _, frequencies_x):
        if not all(f >= 0 for f in frequencies_x):
            raise ValueError("Frequencies must be positive.")

    @frequencies_y.validator  # type: ignore
    def validate_frequencies_y(self, _, frequencies_y):
        if not all(f >= 0 for f in frequencies_y):
            raise ValueError("Frequencies must be positive.")

    @phases_x.validator  # type: ignore
    def validate_phases_x(self, _, phases_x):
        if not len(phases_x) == len(self.frequencies_x):
            raise ValueError(
                "The number of phases must be equal to the number of frequencies."
            )

    @phases_y.validator  # type: ignore
    def validate_phases_y(self, _, phases_y):
        if not len(phases_y) == len(self.frequencies_y):
            raise ValueError(
                "The number of phases must be equal to the number of frequencies."
            )

    @amplitudes_x.validator  # type: ignore
    def validate_amplitude_x(self, _, amplitude_x):
        if not len(amplitude_x) == len(self.frequencies_x):
            raise ValueError(
                "The number of amplitudes must be equal to the number of frequencies."
            )

    @amplitudes_y.validator  # type: ignore
    def validate_amplitude_y(self, _, amplitude_y):
        if not len(amplitude_y) == len(self.frequencies_y):
            raise ValueError(
                "The number of amplitudes must be equal to the number of frequencies."
            )

    @property
    def number_tweezers(self) -> int:
        return self.number_tweezers_along_x * self.number_tweezers_along_y

    @property
    def number_tweezers_along_x(self) -> int:
        return len(self.frequencies_x)

    @property
    def number_tweezers_along_y(self) -> int:
        return len(self.frequencies_y)

    @property
    def segment_frequency(self) -> float:
        return self.sampling_rate / self.number_samples

    def tweezer_positions(self) -> dict[TweezerLabel, tuple[float, float]]:
        positions: dict[TweezerLabel, tuple[float, float]] = {}
        for i, f_x in enumerate(self.frequencies_x):
            for j, f_y in enumerate(self.frequencies_y):
                positions[(i, j)] = (f_x * 1e-6, f_y * 1e-6)
        return positions

    def tweezer_labels(self) -> set[TweezerLabel]:
        return set(self.tweezer_positions().keys())

    @property
    def position_units(self) -> str:
        return "MHz"


def to_tuple_of_float(values: Iterable[SupportsFloat]) -> tuple[float, ...]:
    return tuple(float(v) for v in values)


def schroeder_phases(
    amplitudes: np.ndarray,
    frequencies: np.ndarray,
    period: float,
) -> np.ndarray:
    """Computes the Schroeder phases for a set of amplitudes and frequencies.

    The Schroeder phases are empirical phases that minimize the peak value of the signal envelope.

    Args:
        amplitudes: Amplitudes of the tones. Must be an array of real numbers with length equal to the number of
            tones.
        frequencies: Frequencies of the tones. Must be integer multiples of the signal frequency. Must be an array of
            real numbers with length equal to the number of tones.
        period: Period of the signal.
    """

    number_tones = len(amplitudes)

    powers = amplitudes**2 / 2
    relative_powers = powers / np.sum(powers)

    harmonics = frequencies * period
    if not np.allclose(harmonics, np.round(harmonics)):
        raise ValueError(
            "Cannot compute Schroeder phases for a signal whose frequencies are not integer multiples of the signal "
            "frequency."
        )
    phases = []
    for tone in range(number_tones):
        phase = (
            2
            * np.pi
            * np.sum((harmonics[tone] - harmonics[:tone]) * relative_powers[:tone])
        )
        phases.append(phase)
    return np.array(phases) % (2 * np.pi)


def compute_signal(times, amplitudes, frequencies, phases):
    return sum(
        amplitude * np.sin(2 * np.pi * times * frequency + phase)
        for amplitude, frequency, phase in zip(
            amplitudes, frequencies, phases, strict=True
        )
    )


def closest_harmonics(frequencies: ArrayLike, fundamental: float):
    return np.round(np.array(frequencies) / fundamental).astype(int)


def are_frequencies_multiple_of_fundamental(
    frequencies: ArrayLike, fundamental: float
) -> bool:
    fractional_parts = np.array(frequencies) / fundamental - closest_harmonics(
        frequencies, fundamental
    )
    return np.allclose(fractional_parts, 0)


def compute_all_frequencies_beating(harmonics: Sequence[int], order: int) -> set[int]:
    """Computes all possible sum/difference of `order` frequencies.

    This will compute all values of the form :math:`|h_{i_1} \\pm h_{i_2} \\pm ... \\pm h_{i_n}|` where :math:`n` is the
    order and :math:`h_i` are the values in `harmonics`.
    """

    f = np.concatenate([-np.array(harmonics), np.array(harmonics)])
    return set(
        Counter(map(lambda x: abs(sum(x)), itertools.product(f, repeat=order))).keys()
    )


def compute_smallest_frequency_beating(
    frequencies: ArrayLike, fundamental: float, order: int
) -> float:
    """Computes the smallest non-zero frequency beating of a given order."""

    harmonics = closest_harmonics(frequencies, fundamental)
    beats = compute_all_frequencies_beating(harmonics, order)
    beats = beats - {0}
    return min(beats) * fundamental


YAMLSerializable.register_attrs_class(AODTweezerConfiguration)

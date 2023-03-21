import logging
from collections import defaultdict, Counter
from collections.abc import Sequence
from itertools import product, chain
from typing import Iterable

import numpy as np

# from numba import njit, float64, prange
from pydantic import validator, Field, BaseModel
from scipy.optimize import basinhopping
from trap_signal_generator.configuration import StaticTrapConfiguration

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class StaticTrapGenerator(BaseModel):
    frequencies: Sequence[float] = Field()
    amplitudes: Sequence[float] = Field()
    phases: Sequence[float] = Field()
    sampling_rate: float = Field(gt=0)
    number_samples: int = Field(gt=0)

    class Config:
        validate_assignment = True
        arbitrary_types_allowed = True
        validate_all = True

    @validator("frequencies", pre=True)
    def validate_frequencies(cls, frequencies):
        return tuple(frequencies)

    @validator("amplitudes", pre=True)
    def validate_amplitudes(cls, amplitudes, values):
        frequencies = values["frequencies"]
        if len(amplitudes) != len(frequencies):
            raise ValueError(
                "Number of amplitudes must be the same than the number of frequencies"
            )
        return tuple(amplitudes)

    @validator("phases", pre=True)
    def validate_phases(cls, phases, values):
        frequencies = values["frequencies"]
        if len(phases) != len(frequencies):
            raise ValueError(
                "Number of phases must be the same than the number of frequencies"
            )
        return tuple(phases)

    def compute_signal(self) -> np.ndarray["number_samples", np.float32]:
        return compute_signal(
            times=np.array(self.times, dtype=np.float64),
            amplitudes=np.array(self.amplitudes, dtype=np.float64),
            frequencies=np.array(self.frequencies, dtype=np.float64),
            phases=np.array(self.phases, dtype=np.float64),
        )

    @property
    def times(self):
        return np.arange(self.number_samples) / self.sampling_rate

    def optimize_phases(self):
        """Changes its phases to reduce the peak values of the signal envelope."""

        if not self.is_periodic():
            raise ValueError(
                "Cannot optimize phases for a signal whose frequencies are not integer multiples of the signal "
                "frequency."
            )

        optimal_phases = compute_optimized_phases(
            self.frequencies, self.amplitudes, self.segment_frequency
        )
        self.phases = optimal_phases % (2 * np.pi)

    @property
    def segment_frequency(self):
        return self.sampling_rate / self.number_samples

    def is_periodic(self):
        fractional_parts = (
            np.array(self.frequencies) / self.segment_frequency
            - self._integer_frequencies
        )
        return np.allclose(fractional_parts, 0)

    @property
    def _integer_frequencies(self):
        return np.round(np.array(self.frequencies) / self.segment_frequency).astype(int)

    def compute_all_frequencies_beating(self, order: int):
        """Computes all possible sum of order frequencies beating."""

        if not self.is_periodic():
            raise ValueError(
                "Cannot compute beating frequencies for a signal whose frequencies are not integer multiples of the "
                "signal frequency."
            )

        f = np.concatenate([self._integer_frequencies, -self._integer_frequencies])
        beats = np.array(
            sorted(Counter(map(lambda x: abs(sum(x)), product(f, repeat=order))).keys())
        )
        return beats * self.segment_frequency

    def compute_smallest_frequency_beating(self, order: int):
        """Computes the smallest frequency beating."""

        beats = self.compute_all_frequencies_beating(order)
        beats = beats[beats > self.segment_frequency / 2]
        return np.min(beats)

    # noinspection PyTypeChecker
    def get_configuration(self) -> StaticTrapConfiguration:
        return StaticTrapConfiguration(
            frequencies=np.array(self.frequencies).tolist(),
            amplitudes=np.array(self.amplitudes).tolist(),
            phases=np.array(self.phases).tolist(),
            sampling_rate=self.sampling_rate,
            number_samples=self.number_samples,
        )

    @classmethod
    def from_configuration(cls, config: StaticTrapConfiguration):
        return cls(
            frequencies=config.frequencies,
            amplitudes=config.amplitudes,
            phases=config.phases,
            sampling_rate=config.sampling_rate,
            number_samples=config.number_samples,
        )

    @property
    def number_tones(self):
        return len(self.frequencies)


def compute_signal(times, amplitudes, frequencies, phases):
    return sum(
        amplitude * np.sin(2 * np.pi * times * frequency + phase)
        for amplitude, frequency, phase in zip(
            amplitudes, frequencies, phases, strict=True
        )
    )


# @njit(parallel=True)
# def compute_signal_numba(
#     times: float64[:],
#     amplitudes: float64[:],
#     frequencies: float64[:],
#     phases: float64[:],
# ) -> float64[:]:
#     result = np.zeros_like(times)
#     t = times
#     number_tones = len(amplitudes)
#     for tone in prange(number_tones):
#         amplitude = amplitudes[tone]
#         frequency = frequencies[tone]
#         phase = phases[tone]
#
#         result += amplitude * np.sin(2 * np.pi * t * frequency + phase)
#     return result


def compute_optimized_phases(
    frequencies: Sequence[float],
    amplitudes: Sequence[float],
    segment_frequency: float,
    initial_phases: Sequence[float] = None,
):
    amplitudes = np.array(amplitudes)
    frequencies = np.array(frequencies)

    integer_frequencies = np.round(frequencies / segment_frequency).astype(int)
    indexes = np.array(list(_compute_quadruplets(integer_frequencies)))

    def to_minimize(phases):
        a = (amplitudes * np.exp(1j * phases))[indexes]
        return np.real(np.sum(a[:, 0] * np.conj(a[:, 1]) * np.conj(a[:, 2]) * a[:, 3]))

    if initial_phases:
        initial_phases = np.array(initial_phases)
    else:
        initial_phases = np.random.uniform(0, 2 * np.pi, len(frequencies))

    solution = basinhopping(to_minimize, initial_phases)
    return solution.x


def _compute_quadruplets(
    frequencies: Sequence[int],
) -> Iterable[tuple[int, int, int, int]]:
    """Computes all indexes i,j,k,l such that frequencies[i]-frequencies[j] == frequencies[k]-frequencies[l]"""

    diffs = defaultdict(list)
    for (i, fi), (j, fj) in product(enumerate(frequencies), repeat=2):
        diffs[fi - fj].append((i, j))

    indexes = chain(
        *map(lambda y: map(lambda x: x[0] + x[1], product(y, repeat=2)), diffs.values())
    )
    return indexes

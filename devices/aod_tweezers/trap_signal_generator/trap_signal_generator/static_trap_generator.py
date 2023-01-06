from collections.abc import Sequence

import numpy as np
from numba import njit, float32, prange
from pydantic import BaseModel, validator, Field


class StaticTrapGenerator(BaseModel):
    frequencies: Sequence[float] = Field(allow_mutation=False)
    amplitudes: Sequence[float] = Field(allow_mutation=False)
    phases: Sequence[float] = Field(allow_mutation=False)
    sampling_rate: float = Field(gt=0, allow_mutation=False)
    number_samples: int = Field(gt=0, allow_mutation=False)

    class Config:
        validate_assignment = True
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
        return compute_signal_numba(
            times=np.array(self.times, dtype=np.float32),
            amplitudes=np.array(self.amplitudes, dtype=np.float32),
            frequencies=np.array(self.frequencies, dtype=np.float32),
            phases=np.array(self.frequencies, dtype=np.float32),
        )

    @property
    def times(self):
        return np.arange(self.number_samples) / self.sampling_rate


@njit(parallel=True)
def compute_signal_numba(
    times: float32[:],
    amplitudes: float32[:],
    frequencies: float32[:],
    phases: float32[:],
) -> float32[:]:
    result = np.zeros_like(times)
    t = times
    number_tones = len(amplitudes)
    for tone in prange(number_tones):
        amplitude = amplitudes[tone]
        frequency = frequencies[tone]
        phase = phases[tone]

        result += amplitude * np.sin(2 * np.pi * t * frequency + phase)
    return result

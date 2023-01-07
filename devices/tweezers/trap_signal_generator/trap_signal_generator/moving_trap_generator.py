from collections.abc import Sequence
from functools import cached_property

import numpy as np
from pydantic import BaseModel, validator
from scipy.integrate import cumtrapz, quad


class MovingTrapGenerator(BaseModel):
    starting_frequencies: Sequence[float]
    target_frequencies: Sequence[float]
    starting_phases: Sequence[float]
    target_phases: Sequence[float]
    amplitudes: Sequence[float]
    sampling_rate: float
    number_samples: int

    class Config:
        validate_assignment = True
        validate_all = True
        keep_untouched = (cached_property,)

    @validator("starting_frequencies", pre=True)
    def validate_starting_frequencies(cls, starting_frequencies):
        return tuple(starting_frequencies)

    @validator("target_frequencies", pre=True)
    def validate_target_frequencies(cls, target_frequencies, values):
        starting_frequencies = values["starting_frequencies"]
        if len(target_frequencies) != len(starting_frequencies):
            raise ValueError(
                "Number of target frequencies must be the same than the number of starting frequencies"
            )
        return tuple(target_frequencies)

    @validator("starting_phases", pre=True)
    def validate_starting_phases(cls, starting_phases, values):
        starting_frequencies = values["starting_frequencies"]
        if len(starting_phases) != len(starting_frequencies):
            raise ValueError(
                "Number of starting phases must be the same than the number of starting frequencies"
            )
        return tuple(starting_phases)

    @validator("target_phases", pre=True)
    def validate_target_phases(cls, target_phases, values):
        starting_frequencies = values["starting_frequencies"]
        if len(target_phases) != len(starting_frequencies):
            raise ValueError(
                "Number of target phases must be the same than the number of starting frequencies"
            )
        return tuple(target_phases)

    @validator("amplitudes", pre=True)
    def validate_amplitudes(cls, amplitudes, values):
        starting_frequencies = values["starting_frequencies"]
        if len(amplitudes) != len(starting_frequencies):
            raise ValueError(
                "Number of amplitudes must be the same than the number of starting frequencies"
            )
        return tuple(amplitudes)

    @staticmethod
    def interpolating_function(x):
        def fun(s):
            return np.sin(np.pi / 2 * s) ** 2

        return np.piecewise(x, (x < 0, x <= 1), (0, fun, 1))

    @cached_property
    def interpolating_function_integral(self):
        return quad(self.interpolating_function, 0, 1)[0]

    def compute_signal(self):
        return np.sum(
            np.array(self.amplitudes)[..., np.newaxis] * np.sin(self.compute_phases()),
            axis=0,
        )

    def compute_phases(
        self,
    ) -> np.ndarray[("number_tones", "number_samples"), np.float]:
        frequencies = self.compute_frequencies()
        starting_phases = np.array(self.starting_phases)[..., np.newaxis]

        return starting_phases + (
            2 * np.pi * cumtrapz(frequencies, x=self.times, initial=0)
        )

    def compute_frequencies(
        self,
    ) -> np.ndarray[("number_tones", "number_samples"), np.float]:
        starting_frequencies = np.array(self.starting_frequencies)[..., np.newaxis]
        target_frequencies = np.array(self.target_frequencies)[..., np.newaxis]

        stop_intervals = self.compute_stop_interval()[..., np.newaxis]

        frequencies = starting_frequencies + (
            target_frequencies - starting_frequencies
        ) * self.interpolating_function(self.times / (self.duration - stop_intervals))
        return frequencies

    def compute_stop_interval(self):
        starting_frequencies = np.array(self.starting_frequencies)
        target_frequencies = np.array(self.target_frequencies)
        frequency_differences = target_frequencies - starting_frequencies

        starting_phases = np.array(self.starting_phases)
        target_phases = np.array(self.target_phases)
        phase_differences = target_phases - starting_phases

        integral = self.interpolating_function_integral
        result = (
            -(2 * np.pi * self.duration)
            * (starting_frequencies + integral * frequency_differences)
            + phase_differences
        ) % (2 * np.pi)
        return result / (2 * np.pi * frequency_differences * (1 - integral))

    @property
    def times(self):
        return np.arange(self.number_samples) / self.sampling_rate

    @property
    def duration(self):
        return self.number_samples / self.sampling_rate

    @property
    def number_tones(self):
        return len(self.amplitudes)

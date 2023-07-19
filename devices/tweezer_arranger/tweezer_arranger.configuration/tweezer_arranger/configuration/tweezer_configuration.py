from abc import ABC, abstractmethod
from typing import Protocol, Hashable

from pydantic import validator, Field

from settings_model import SettingsModel


class TweezerLabel(Hashable, Protocol):
    def __str__(self) -> str:
        ...


class TweezerConfiguration(ABC):
    """Contains the information to generate a static pattern of traps."""

    @property
    @abstractmethod
    def number_tweezers(self) -> int:
        """The total number of tweezers in the configuration."""
        raise NotImplementedError

    @abstractmethod
    def tweezer_labels(self) -> set[TweezerLabel]:
        """The unique labels of the tweezers in the configuration."""
        raise NotImplementedError

    @property
    @abstractmethod
    def position_units(self) -> str:
        """The units of the tweezer positions.

        This is mostly for documentation and plotting purposes, it can be different that what is used to store the
        parameters. Typical values can be "μm".
        """
        raise NotImplementedError


class TweezerConfiguration1D(TweezerConfiguration):
    @abstractmethod
    def tweezer_positions(self) -> dict[TweezerLabel, float]:
        raise NotImplementedError


class TweezerConfiguration2D(TweezerConfiguration):
    @abstractmethod
    def tweezer_positions(self) -> dict[TweezerLabel, tuple[float, float]]:
        raise NotImplementedError


class AODTweezerConfiguration(SettingsModel, TweezerConfiguration2D):
    """Contains the information to generate a grid of trap with an AOD/AWG.

    Fields:
        frequencies_x: The frequencies of each tone in Hz.
        phases_x: The phases of each tone in radian.
        amplitude_x: The amplitudes of each tone. They have no dimension.
        scale_x: The value to multiply the x-signal by to get the voltage to send to the AWG. Must be in V.
        frequencies_y: The frequencies of each tone in Hz.
        phases_y: The phases of each tone in radian.
        amplitude_y: The amplitudes of each tone. They have no dimension.
        scale_y: The value to multiply the y-signal by to get the voltage to send to the AWG. Must be in V.
        sampling_rate: The sampling rate of the AWG to generate the signal, in Hz.
        number_samples: The number of samples of the waveform. To generate a signal for longer times than
        number_samples / sampling_rate, the waveform is repeated.
    """

    frequencies_x: tuple[float, ...]
    phases_x: tuple[float, ...]
    amplitudes_x: tuple[float, ...]
    scale_x: float = Field(ge=0.0)
    frequencies_y: tuple[float, ...]
    phases_y: tuple[float, ...]
    amplitudes_y: tuple[float, ...]
    scale_y: float = Field(ge=0.0)

    sampling_rate: float = Field(ge=0.0)
    number_samples: int = Field(ge=1)

    @validator("frequencies_x")
    def validate_frequencies_x(cls, frequencies_x):
        if not all(f >= 0 for f in frequencies_x):
            raise ValueError("Frequencies must be positive.")
        return frequencies_x

    @validator("frequencies_y")
    def validate_frequencies_y(cls, frequencies_y):
        if not all(f >= 0 for f in frequencies_y):
            raise ValueError("Frequencies must be positive.")
        return frequencies_y

    @validator("phases_x")
    def validate_phases_x(cls, phases_x, values):
        if not len(phases_x) == len(values["frequencies_x"]):
            raise ValueError(
                "The number of phases must be equal to the number of frequencies."
            )
        return phases_x

    @validator("phases_y")
    def validate_phases_y(cls, phases_y, values):
        if not len(phases_y) == len(values["frequencies_y"]):
            raise ValueError(
                "The number of phases must be equal to the number of frequencies."
            )
        return phases_y

    @validator("amplitudes_x")
    def validate_amplitude_x(cls, amplitude_x, values):
        if not len(amplitude_x) == len(values["frequencies_x"]):
            raise ValueError(
                "The number of amplitudes must be equal to the number of frequencies."
            )
        return amplitude_x

    @validator("amplitudes_y")
    def validate_amplitude_y(cls, amplitude_y, values):
        if not len(amplitude_y) == len(values["frequencies_y"]):
            raise ValueError(
                "The number of amplitudes must be equal to the number of frequencies."
            )
        return amplitude_y

    @property
    def number_tweezers(self) -> int:
        return self.number_tweezers_along_x * self.number_tweezers_along_y

    @property
    def number_tweezers_along_x(self) -> int:
        return len(self.frequencies_x)

    @property
    def number_tweezers_along_y(self) -> int:
        return len(self.frequencies_y)

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

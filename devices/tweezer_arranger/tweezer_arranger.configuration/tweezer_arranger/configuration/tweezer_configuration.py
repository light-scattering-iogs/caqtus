from abc import ABC, abstractmethod
from typing import Protocol, Hashable

from pydantic import validator

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

        This is mostly for documentation and plotting purposes. Typical values can be "μm".
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
    frequencies_x: tuple[float, ...]
    phases_x: tuple[float, ...]
    amplitude_x: tuple[float, ...]
    frequencies_y: tuple[float, ...]
    phases_y: tuple[float, ...]
    amplitude_y: tuple[float, ...]

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

    @validator("amplitude_x")
    def validate_amplitude_x(cls, amplitude_x, values):
        if not len(amplitude_x) == len(values["frequencies_x"]):
            raise ValueError(
                "The number of amplitudes must be equal to the number of frequencies."
            )
        return amplitude_x

    @validator("amplitude_y")
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
                positions[(i, j)] = (f_x, f_y)
        return positions

    def tweezer_labels(self) -> set[TweezerLabel]:
        return set(self.tweezer_positions().keys())

    @property
    def position_units(self) -> str:
        return "MHz"

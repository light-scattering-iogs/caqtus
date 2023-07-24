from abc import ABC, abstractmethod
from typing import Protocol, Hashable


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

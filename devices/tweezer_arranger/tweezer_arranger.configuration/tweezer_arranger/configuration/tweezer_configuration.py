from abc import ABC, abstractmethod
from typing import Protocol, Hashable


class TweezerLabel(Hashable, Protocol):
    def __str__(self) -> str:
        ...


class TweezerConfiguration(ABC):
    """Abstract class that define the interface to generate a static pattern of traps.

    It is meant to be subclassed by a concrete class that implements the actual configuration. For example, the
    configuration of the tweezers could be defined by the frequencies to apply to an AOD or by the phases to apply to a
    SLM.
    """

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
        device parameters. Typical values can be "μm".
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

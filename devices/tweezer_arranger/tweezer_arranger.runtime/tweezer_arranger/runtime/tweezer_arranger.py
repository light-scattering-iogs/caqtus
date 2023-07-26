from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar, Generic

from pydantic import Field

from device.runtime import RuntimeDevice
from tweezer_arranger.configuration import (
    TweezerConfiguration,
    TweezerConfigurationName,
)

TweezerConfigurationType = TypeVar(
    "TweezerConfigurationType", bound=TweezerConfiguration
)


class ArrangerInstruction(ABC):
    pass


@dataclass
class HoldTweezers(ArrangerInstruction):
    tweezer_configuration: TweezerConfigurationName
    duration: float


@dataclass
class MoveTweezers(ArrangerInstruction):
    initial_tweezer_configuration: TweezerConfigurationName
    final_tweezer_configuration: TweezerConfigurationName
    duration: float


class TweezerArranger(RuntimeDevice, ABC, Generic[TweezerConfigurationType]):
    """Abstract class that define the interface for a device that can move and rearrange tweezers.

    This class is meant to be inherited by a concrete class that implements the actual rearrangement. It is generic on
    the type of the configuration of the tweezers, which is should be defined by the concrete class.

    Fields:
        tweezer_configurations: The configurations between which the tweezers can be moved.
    """

    tweezer_configurations: dict[
        TweezerConfigurationName, TweezerConfigurationType
    ] = Field(allow_mutation=False)

    @abstractmethod
    def update_parameters(self, *, instructions: Sequence[ArrangerInstruction]) -> None:
        raise NotImplementedError

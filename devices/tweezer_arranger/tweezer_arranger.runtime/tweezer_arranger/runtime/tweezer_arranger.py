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
    tweezer_configurations: dict[
        TweezerConfigurationName, TweezerConfigurationType
    ] = Field(allow_mutation=False)

    @abstractmethod
    def update_parameters(self, *, instructions: Sequence[ArrangerInstruction]) -> None:
        raise NotImplementedError

from abc import ABC
from dataclasses import dataclass

from .arranger_configuration import TweezerConfigurationName


@dataclass(frozen=True)
class ArrangerInstruction(ABC):
    pass


@dataclass(frozen=True)
class HoldTweezers(ArrangerInstruction):
    tweezer_configuration: TweezerConfigurationName


@dataclass(frozen=True)
class MoveTweezers(ArrangerInstruction):
    initial_tweezer_configuration: TweezerConfigurationName
    final_tweezer_configuration: TweezerConfigurationName


@dataclass(frozen=True)
class RearrangeTweezers(ArrangerInstruction):
    initial_tweezer_configuration: TweezerConfigurationName
    final_tweezer_configuration: TweezerConfigurationName

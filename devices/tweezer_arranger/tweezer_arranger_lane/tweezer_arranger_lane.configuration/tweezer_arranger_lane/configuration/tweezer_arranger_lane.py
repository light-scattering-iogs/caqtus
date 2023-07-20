from abc import ABC, abstractmethod
from typing import Self

from lane.configuration import Lane
from settings_model import SettingsModel
from tweezer_arranger.configuration import TweezerConfigurationName


class TweezerAction(SettingsModel, ABC):
    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError


class HoldTweezers(TweezerAction):
    configuration: TweezerConfigurationName

    def __str__(self) -> str:
        return self.configuration

    @classmethod
    def default(cls) -> Self:
        return cls(configuration=TweezerConfigurationName("..."))


class MoveTweezers(TweezerAction):
    def __str__(self):
        return "Move"

    @classmethod
    def default(cls) -> Self:
        return cls()


class RearrangeTweezers(TweezerAction):
    def __str__(self):
        return "Rearrange"

    @classmethod
    def default(cls) -> Self:
        return cls()


class TweezerArrangerLane(Lane[TweezerAction]):
    pass

from abc import ABC, abstractmethod

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


class MoveTweezers(TweezerAction):
    def __str__(self):
        return "Move"


class TweezerArrangerLane(Lane[TweezerAction]):
    pass

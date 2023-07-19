from abc import ABC

from lane.configuration import Lane
from settings_model import SettingsModel
from tweezer_arranger.configuration import TweezerConfigurationName


class TweezerAction(SettingsModel, ABC):
    pass


class HoldTweezers(TweezerAction):
    configuration: TweezerConfigurationName


class MoveTweezers(TweezerAction):
    pass


class TweezerArrangerLane(Lane[TweezerAction]):
    pass

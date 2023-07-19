from abc import ABC

from settings_model import SettingsModel


class TweezerArrangerAction(SettingsModel, ABC):
    pass


class HoldTweezers(TweezerArrangerAction):
    picture_name: str

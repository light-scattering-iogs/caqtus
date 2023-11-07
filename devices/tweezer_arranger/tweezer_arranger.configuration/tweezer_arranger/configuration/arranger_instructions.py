import abc

from tweezer_arranger_lane.configuration import MoveType
from util import attrs
from .arranger_configuration import TweezerConfigurationName


@attrs.frozen
class ArrangerInstruction(abc.ABC):
    pass


@attrs.frozen
class HoldTweezers(ArrangerInstruction):
    tweezer_configuration: TweezerConfigurationName


@attrs.frozen
class MoveTweezers(ArrangerInstruction):
    initial_tweezer_configuration: TweezerConfigurationName
    final_tweezer_configuration: TweezerConfigurationName
    move_type: MoveType


@attrs.frozen
class RearrangeTweezers(ArrangerInstruction):
    initial_tweezer_configuration: TweezerConfigurationName
    final_tweezer_configuration: TweezerConfigurationName
    move_type: MoveType

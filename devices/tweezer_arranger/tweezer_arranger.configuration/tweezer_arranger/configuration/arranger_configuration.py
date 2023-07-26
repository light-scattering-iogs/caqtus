from abc import ABC
from collections.abc import Set, Sequence
from typing import Generic, TypeVar, Any

from configuration_holder import ConfigurationHolder
from device.configuration import DeviceConfiguration, DeviceParameter
from tweezer_arranger.configuration_name import TweezerConfigurationName
from tweezer_arranger_lane.configuration import (
    TweezerAction,
    HoldTweezers as HoldTweezersLane,
    MoveTweezers as MoveTweezersLane,
    RearrangeTweezers as RearrangeTweezersLane,
)
from .arranger_instructions import (
    ArrangerInstruction,
    HoldTweezers as HoldTweezerInstruction,
    MoveTweezers as MoveTweezerInstruction,
    RearrangeTweezers as RearrangeTweezerInstruction,
)
from .tweezer_configuration import TweezerConfiguration

TweezerConfigurationType = TypeVar(
    "TweezerConfigurationType", bound=TweezerConfiguration
)


class TweezerArrangerConfiguration(
    DeviceConfiguration,
    ConfigurationHolder[TweezerConfigurationName, TweezerConfigurationType],
    ABC,
    Generic[TweezerConfigurationType],
):
    def get_device_init_args(
        self,
        tweezer_configurations_to_use: Set[TweezerConfigurationName],
        tweezer_sequence: Sequence[TweezerAction],
    ) -> dict[DeviceParameter, Any]:
        sequence: list[ArrangerInstruction] = []
        for step, action in enumerate(tweezer_sequence):
            match action:
                case HoldTweezersLane(configuration):
                    sequence.append(HoldTweezerInstruction(configuration))
                case MoveTweezersLane():
                    previous = tweezer_sequence[step - 1]
                    if not isinstance(previous, HoldTweezersLane):
                        raise ValueError(
                            f"Cannot move tweezers at step {step} without holding them first."
                        )
                    following = tweezer_sequence[step + 1]
                    if not isinstance(following, HoldTweezersLane):
                        raise ValueError(
                            f"Cannot move tweezers at step {step} without holding them afterwards."
                        )
                    sequence.append(
                        MoveTweezerInstruction(
                            previous.configuration, following.configuration
                        )
                    )
                case RearrangeTweezersLane():
                    previous = tweezer_sequence[step - 1]
                    if not isinstance(previous, HoldTweezersLane):
                        raise ValueError(
                            f"Cannot rearrange tweezers at step {step} without holding them first."
                        )
                    following = tweezer_sequence[step + 1]
                    if not isinstance(following, HoldTweezersLane):
                        raise ValueError(
                            f"Cannot rearrange tweezers at step {step} without holding them afterwards."
                        )
                    sequence.append(
                        RearrangeTweezerInstruction(
                            previous.configuration, following.configuration
                        )
                    )

        return super().get_device_init_args() | {
            "tweezer_configurations": {
                configuration_name: self[configuration_name]
                for configuration_name in tweezer_configurations_to_use
            },
            "tweezer_sequence": sequence,
        }

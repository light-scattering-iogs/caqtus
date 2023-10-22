from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TypeVar, Generic

from attrs import define, field
from attrs.setters import frozen

from device.runtime import RuntimeDevice
from tweezer_arranger.configuration import (
    TweezerConfiguration,
    TweezerConfigurationName,
    ArrangerInstruction,
    HoldTweezers,
    MoveTweezers,
    RearrangeTweezers,
)

TweezerConfigurationType = TypeVar(
    "TweezerConfigurationType", bound=TweezerConfiguration
)


@define(slots=False)
class TweezerArranger(RuntimeDevice, ABC, Generic[TweezerConfigurationType]):
    """Abstract class that define the interface for a device that can move and rearrange tweezers.

    This class is meant to be inherited by a concrete class that implements the actual rearrangement. It is generic on
    the type of the configuration of the tweezers, which is should be defined by the concrete class.

    Fields:
        tweezer_configurations: The configurations between which the tweezers can be moved.
        tweezer_sequence: The sequence of instructions that define the movement of the tweezers.
    """

    tweezer_configurations: dict[
        TweezerConfigurationName, TweezerConfigurationType
    ] = field(on_setattr=frozen)

    tweezer_sequence: tuple[ArrangerInstruction, ...] = field(on_setattr=frozen)

    @abstractmethod
    def update_parameters(self, *, tweezer_sequence_durations: Sequence[float]) -> None:
        raise NotImplementedError

    @tweezer_sequence.validator  # type: ignore
    def validate_tweezer_sequence(self, _, sequence: tuple[ArrangerInstruction, ...]):
        for index, instruction in enumerate(sequence):
            match instruction:
                case HoldTweezers():
                    if index > 0:
                        previous = sequence[index - 1]
                        if isinstance(previous, HoldTweezers):
                            raise ValueError(
                                "Two consecutive static steps are not allowed"
                            )
                    if index < len(sequence) - 1:
                        following = sequence[index + 1]
                        if isinstance(following, HoldTweezers):
                            raise ValueError(
                                "Two consecutive static steps are not allowed"
                            )
                case MoveTweezers():
                    if index == 0:
                        raise ValueError(
                            "The first step in a tweezer sequence cannot be a move step"
                        )
                    if index == len(sequence) - 1:
                        raise ValueError(
                            "The last step in a tweezer sequence cannot be a move step"
                        )
                case RearrangeTweezers():
                    if index == 0:
                        raise ValueError(
                            "The first step in a tweezer sequence cannot be a rearrange step"
                        )
                    if index == len(sequence) - 1:
                        raise ValueError(
                            "The last step in a tweezer sequence cannot be a rearrange step"
                        )
                case _:
                    raise TypeError("Invalid instruction type")


class RearrangementFailedError(RuntimeError):
    pass

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeVar, Generic

from pydantic import Field, validator

from device.runtime import RuntimeDevice
from tweezer_arranger.configuration import (
    TweezerConfiguration,
    TweezerConfigurationName,
)

TweezerConfigurationType = TypeVar(
    "TweezerConfigurationType", bound=TweezerConfiguration
)


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
    ] = Field(allow_mutation=False)

    tweezer_sequence: tuple[ArrangerInstruction, ...] = Field(allow_mutation=False)

    @abstractmethod
    def update_parameters(self, *, tweezer_sequence_durations: Sequence[float]) -> None:
        raise NotImplementedError

    @validator("tweezer_sequence")
    def validate_tweezer_sequence(
        cls, sequence: tuple[ArrangerInstruction, ...]
    ) -> tuple[ArrangerInstruction, ...]:
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
        return sequence

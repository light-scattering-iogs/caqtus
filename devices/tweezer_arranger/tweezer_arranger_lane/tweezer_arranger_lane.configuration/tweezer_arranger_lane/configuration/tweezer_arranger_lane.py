from abc import ABC, abstractmethod
from typing import Self, Literal

from lane.configuration import Lane
from settings_model import YAMLSerializable
from tweezer_arranger.configuration_name import TweezerConfigurationName
from util import attrs


@attrs.define
class TweezerAction(ABC):
    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError


@attrs.define
class HoldTweezers(TweezerAction):
    configuration: TweezerConfigurationName

    def __str__(self) -> str:
        return self.configuration

    @classmethod
    def default(cls) -> Self:
        return cls(configuration=TweezerConfigurationName("..."))


YAMLSerializable.register_attrs_class(HoldTweezers)


@attrs.define
class MoveType(ABC):
    @abstractmethod
    def __str__(self) -> Literal["sin", "throw"]:
        raise NotImplementedError


@attrs.define
class SinMove(MoveType):
    def __str__(self):
        return "sin"


YAMLSerializable.register_attrs_class(SinMove)


@attrs.define
class ThrowMove(MoveType):
    def __str__(self):
        return "throw"


YAMLSerializable.register_attrs_class(ThrowMove)


@attrs.define
class MoveTweezers(TweezerAction):
    move_type: MoveType = attrs.field(
        factory=SinMove,
        validator=attrs.validators.instance_of(MoveType),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return "Move"

    @classmethod
    def default(cls) -> Self:
        return cls()


YAMLSerializable.register_attrs_class(MoveTweezers)


@attrs.define
class RearrangeTweezers(TweezerAction):
    move_type: MoveType = attrs.field(
        factory=SinMove,
        validator=attrs.validators.instance_of(MoveType),
        on_setattr=attrs.setters.validate,
    )

    def __str__(self):
        return "Rearrange"

    @classmethod
    def default(cls) -> Self:
        return cls()


YAMLSerializable.register_attrs_class(RearrangeTweezers)


class TweezerArrangerLane(Lane[TweezerAction]):
    def get_static_configurations(self) -> set[TweezerConfigurationName]:
        result = set[TweezerConfigurationName]()
        for cell_value, _, _ in self.get_value_spans():
            if isinstance(cell_value, HoldTweezers):
                result.add(cell_value.configuration)

        return result

    def list_steps(self) -> list[TweezerAction]:
        return [cell_value for cell_value, _, _ in self.get_value_spans()]

    def get_rearrangement_steps(self) -> list[tuple[int, int, int]]:
        result = []
        for step, (cell_value, start, stop) in enumerate(self.get_value_spans()):
            if isinstance(cell_value, RearrangeTweezers):
                result.append((step, start, stop))
        return result

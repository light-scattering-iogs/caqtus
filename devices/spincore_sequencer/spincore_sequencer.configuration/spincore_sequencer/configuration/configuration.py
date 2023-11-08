from typing import Any, ClassVar, Type

from device.configuration import DeviceParameter
from sequencer.configuration import (
    SequencerConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
)
from settings_model import YAMLSerializable
from util import attrs


@attrs.define(slots=False)
class SpincoreSequencerConfiguration(SequencerConfiguration):
    """Holds the static configuration of a spincore sequencer device.

    Fields:
        board_number: The number of the board to use. With only one board connected,
            this number is usually 0.
        time_step: The quantization time step used. All times during a run are multiples
            of this value.
    """

    @classmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]:
        return (DigitalChannelConfiguration,) * cls.number_channels

    number_channels: ClassVar[int] = 24

    board_number: int = attrs.field(
        converter=int,
        on_setattr=attrs.setters.convert,
    )
    channels: tuple[DigitalChannelConfiguration, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(DigitalChannelConfiguration)
        ),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    time_step: int = attrs.field(
        default=50,
        converter=int,
        validator=attrs.validators.ge(50),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    def get_device_type(self) -> str:
        return "SpincorePulseBlaster"

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        extra = {
            DeviceParameter("board_number"): self.board_number,
            DeviceParameter("time_step"): self.time_step,
        }
        return super().get_device_init_args() | extra


YAMLSerializable.register_attrs_class(SpincoreSequencerConfiguration)

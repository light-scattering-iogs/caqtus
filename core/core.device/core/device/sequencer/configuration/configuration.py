from abc import ABC, abstractmethod
from typing import Type, Any, ClassVar

import attrs

from .channel_output import ChannelOutput, is_channel_output
from .trigger import Trigger, is_trigger
from ...configuration import DeviceConfigurationAttrs, DeviceParameter


def validate_channel_output(instance, attribute, value):
    if not is_channel_output(value):
        raise TypeError(f"Output {value} is not of type ChannelOutput")


@attrs.define
class ChannelConfiguration(ABC):
    """Contains information to computer the output of a channel."""

    description: str = attrs.field(
        converter=str,
        on_setattr=attrs.setters.convert,
    )
    output: ChannelOutput = attrs.field(
        validator=validate_channel_output,
        on_setattr=attrs.setters.validate,
    )


# def color_unstructure(color: Color):
#     return color.original()
#
#
# serialization.register_unstructure_hook(Color, color_unstructure)
#
#
# def color_structure(color: Any, _) -> Color:
#     return Color(color)
#
#
# serialization.register_structure_hook(Color, color_structure)


@attrs.define
class DigitalChannelConfiguration(ChannelConfiguration):
    pass


@attrs.define
class AnalogChannelConfiguration(ChannelConfiguration):
    pass


def validate_trigger(instance, attribute, value):
    if not is_trigger(value):
        raise TypeError(f"Trigger {value} is not of type Trigger")


@attrs.define
class SequencerConfiguration(DeviceConfigurationAttrs, ABC):
    """Holds the static configuration of a sequencer device.

    Fields:
        number_channels: The number of channels of the device.
        time_step: The quantization time step used, in nanoseconds. The device can only
            update its output at multiples of this time step.
        channels: The configuration of the channels of the device. The length of this
            list must match the number of channels of the device.
    """

    number_channels: ClassVar[int]
    time_step: int = attrs.field(
        converter=int,
        validator=attrs.validators.ge(1),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    channels: tuple[ChannelConfiguration, ...] = attrs.field(
        converter=tuple,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(ChannelConfiguration)
        ),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )
    trigger: Trigger = attrs.field(validator=validate_trigger)

    @classmethod
    @abstractmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]:
        ...

    @channels.validator  # type: ignore
    def validate_channels(self, _, channels):
        if len(channels) != self.number_channels:
            raise ValueError(
                f"The length of channels ({len(channels)}) doesn't match the number of"
                f" channels {self.number_channels}"
            )
        for channel, channel_type in zip(channels, self.channel_types(), strict=True):
            if not isinstance(channel, channel_type):
                raise TypeError(
                    f"Channel {channel} is not of the expected type {channel_type}"
                )

    def __getitem__(self, item):
        return self.channels[item]

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        extra = {DeviceParameter("trigger"): self.trigger}
        return super().get_device_init_args(*args, **kwargs) | extra

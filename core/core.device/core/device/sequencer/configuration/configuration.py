from abc import ABC, abstractmethod
from typing import Optional, NewType, TypeVar, Type, TypeGuard, Any, ClassVar, Generic

import attrs
from pydantic.color import Color

from util import serialization
from .channel_mapping import OutputMapping, DigitalMapping, AnalogMapping
from .trigger import Trigger
from ...configuration import DeviceConfigurationAttrs, DeviceParameter

ChannelName = NewType("ChannelName", str)


def is_channel_name(name: Any) -> TypeGuard[ChannelName]:
    return isinstance(name, str)


MappingType = TypeVar("MappingType", bound=OutputMapping)


@attrs.define
class ChannelSpecialPurpose:
    purpose: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)

    def __hash__(self):
        return hash(self.purpose)

    def __str__(self):
        return self.purpose

    @classmethod
    def unused(cls):
        return cls(purpose="Unused")

    def is_unused(self) -> bool:
        return self.purpose == "Unused"


LogicalType = TypeVar("LogicalType")
OutputType = TypeVar("OutputType")


@attrs.define
class ChannelConfiguration(Generic[LogicalType, OutputType], ABC):
    """Contains information to configure the output of a channel.

    This is used to translate from logical values to output values. The logical values
    are the values that are asked for in the sequence. The output values are the values
    that are actually output on the channel.

    Fields:
        description: The name of the lane that should be output on this channel or a
            special purpose if the channel is used for something else, like triggering a
            camera or another sequencer.
        output_mapping: A mapping from the logical values of the channel to the output
            values. This is used to translate human-readable values to the actual values
            that are output on the channel.
        default_value: The default value of the channel. This is the value that is
            output when the channel is not used.
        before_value: The value to use for the channel before the first step of the
            sequence.
        after_value: The value to use for the channel after the last step of the
            sequence.
        color: The color to use for the channel in the GUI.
        delay: The delay to apply to the channel. This is used to compensate for the
            delay between the logical time and the actual effect of the channel. A
            positive delay means that the output is retarder, i.e. its output will
            change after the logical time.
    """

    description: ChannelName | ChannelSpecialPurpose = attrs.field(
        validator=attrs.validators.instance_of((str, ChannelSpecialPurpose)),
        on_setattr=attrs.setters.validate,
    )
    output_mapping: OutputMapping[LogicalType, OutputType]
    default_value: LogicalType
    color: Optional[Color] = attrs.field(
        default=None,
        converter=attrs.converters.optional(Color),
        on_setattr=attrs.setters.convert,
    )
    delay: float = attrs.field(
        default=0.0, converter=float, on_setattr=attrs.setters.convert
    )

    def has_special_purpose(self) -> bool:
        return isinstance(self.description, ChannelSpecialPurpose)

    def is_unused(self) -> bool:
        return self.has_special_purpose() and self.description.is_unused()


def description_structure(description: Any, _) -> str | ChannelSpecialPurpose:
    if isinstance(description, str):
        return description
    elif isinstance(description, dict):
        return ChannelSpecialPurpose(purpose=description["purpose"])
    else:
        raise TypeError(f"Can't construct description from {description}")


serialization.register_structure_hook(
    ChannelName | ChannelSpecialPurpose, description_structure
)


def color_unstructure(color: Color):
    return color.original()


serialization.register_unstructure_hook(Color, color_unstructure)


def color_structure(color: Any, _) -> Color:
    return Color(color)


serialization.register_structure_hook(Color, color_structure)


@attrs.define
class DigitalChannelConfiguration(ChannelConfiguration[bool, bool]):
    output_mapping: DigitalMapping = attrs.field(
        validator=attrs.validators.instance_of(DigitalMapping),
        on_setattr=attrs.setters.validate,
    )
    default_value: bool = attrs.field(
        default=False, converter=bool, on_setattr=attrs.setters.convert
    )
    # We need to redefine these fields just because they have default values and can't
    # come above output_mapping.
    color: Optional[Color] = attrs.field(
        default=None,
        converter=attrs.converters.optional(Color),
        on_setattr=attrs.setters.convert,
    )
    delay: float = attrs.field(
        default=0.0, converter=float, on_setattr=attrs.setters.convert
    )


@attrs.define
class AnalogChannelConfiguration(ChannelConfiguration[float, float]):
    output_mapping: AnalogMapping = attrs.field(
        validator=attrs.validators.instance_of(AnalogMapping),
        on_setattr=attrs.setters.validate,
    )
    default_value: float = attrs.field(
        default=0.0, converter=float, on_setattr=attrs.setters.convert
    )
    # We need to redefine these fields just because they have default values and can't
    # come above output_mapping.
    color: Optional[Color] = attrs.field(
        default=None,
        converter=attrs.converters.optional(Color),
        on_setattr=attrs.setters.convert,
    )
    delay: float = attrs.field(
        default=0.0, converter=float, on_setattr=attrs.setters.convert
    )


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
    trigger: Trigger = attrs.field(validator=attrs.validators.instance_of(Trigger))

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

    def get_lane_channels(self) -> list[ChannelConfiguration]:
        """Get the channels associated to a lane, i.e. those without special purpose"""
        return [
            channel for channel in self.channels if not channel.has_special_purpose()
        ]

    def __getitem__(self, item):
        return self.channels[item]

    def get_channel_index(self, name: ChannelName) -> int:
        for i, channel in enumerate(self.channels):
            if channel.description == name:
                return i
        raise KeyError(f"Channel {name} not found")

    def get_maximum_delay(self) -> float:
        return max(channel.delay for channel in self.channels)

    def get_device_init_args(self, *args, **kwargs) -> dict[DeviceParameter, Any]:
        extra = {DeviceParameter("trigger"): self.trigger}
        return super().get_device_init_args(*args, **kwargs) | extra

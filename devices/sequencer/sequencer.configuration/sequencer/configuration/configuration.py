from abc import ABC, abstractmethod
from typing import Optional, NewType, TypeVar, Type, TypeGuard, Any, ClassVar

from pydantic import validator, Field
from pydantic.color import Color

from device.configuration import DeviceConfiguration
from settings_model import SettingsModel, yaml
from .channel_mapping import OutputMapping, DigitalMapping, AnalogMapping

ChannelName = NewType("ChannelName", str)


def is_channel_name(name: Any) -> TypeGuard[ChannelName]:
    return isinstance(name, str)


MappingType = TypeVar("MappingType", bound=OutputMapping)


class ChannelSpecialPurpose(SettingsModel):
    purpose: str

    def __hash__(self):
        return hash(self.purpose)

    def __str__(self):
        return self.purpose

    @classmethod
    def representer(cls, dumper: yaml.Dumper, channel_purpose: "ChannelSpecialPurpose"):
        return dumper.represent_scalar(f"!{cls.__name__}", channel_purpose.purpose)

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        if not isinstance(node, yaml.ScalarNode):
            raise ValueError(
                f"Cannot construct {cls.__name__} from {node}. Expected a scalar node"
            )
        purpose = loader.construct_scalar(node)
        if not isinstance(purpose, str):
            raise ValueError(
                f"Cannot construct {cls.__name__} from {node}. Expected a string"
            )
        return cls(purpose=purpose)

    @classmethod
    def unused(cls):
        return cls(purpose="Unused")


LogicalType = TypeVar("LogicalType")
OutputType = TypeVar("OutputType")


# Generic[LogicalType, OutputType]
class ChannelConfiguration(SettingsModel, ABC):
    """Contains information to configure the output of a channel.

    This is used to translate from logical values to output values. The logical values are the values that are asked
    for in the sequence. The output values are the values that are actually output on the channel.

    Fields:
        description: The name of the lane that should be output on this channel or a special purpose if the channel is
            used for something else, like triggering a camera or another sequencer.
        output_mapping: A mapping from the logical values of the channel to the output valued. This is used to translate
            human-readable values to the actual values that are output on the channel.
        default_value: The default value of the channel. This is the value that is output when the channel is not used.
        before_value: The value to use for the channel before the first step of the sequence.
        after_value: The value to use for the channel after the last step of the sequence.
        color: The color to use for the channel in the GUI.
        delay: The delay to apply to the channel. This is used to compensate for the delay between the logical time and
            the actual effect of the channel. A positive delay means that the output is retarder, i.e. its output will
            change after the logical time.
    """

    description: ChannelName | ChannelSpecialPurpose
    output_mapping: OutputMapping#[LogicalType, OutputType]
    default_value: Any#LogicalType
    color: Optional[Color] = None
    delay: float = 0.0

    def has_special_purpose(self) -> bool:
        return isinstance(self.description, ChannelSpecialPurpose)


# ChannelConfiguration[bool, bool]
class DigitalChannelConfiguration(ChannelConfiguration):
    output_mapping: DigitalMapping
    default_value: bool = False


# ChannelConfiguration[float, float]
class AnalogChannelConfiguration(ChannelConfiguration):
    output_mapping: AnalogMapping
    default_value: float = 0.0


class SequencerConfiguration(DeviceConfiguration, ABC):
    """Holds the static configuration of a sequencer device.

    Fields:
        number_channels: The number of channels of the device.
        time_step: The quantization time step used, in nanoseconds. The device can only update its output at multiples
            of this time step.
        channels: The configuration of the channels of the device. The length of this list must match the number of
            channels of the device.
    """

    number_channels: ClassVar[int]
    time_step: int = Field(ge=1)
    channels: tuple[ChannelConfiguration, ...]

    @classmethod
    @abstractmethod
    def channel_types(cls) -> tuple[Type[ChannelConfiguration], ...]:
        ...

    @validator("channels")
    def validate_channels(cls, channels):
        if len(channels) != cls.number_channels:
            raise ValueError(
                f"The length of channels ({len(channels)}) doesn't match the number of"
                f" channels {cls.number_channels}"
            )
        for channel, channel_type in zip(channels, cls.channel_types(), strict=True):
            if not isinstance(channel, channel_type):
                raise TypeError(
                    f"Channel {channel} is not of the expected type {channel_type}"
                )
        return channels

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

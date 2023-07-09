from abc import ABC, abstractmethod
from typing import Optional, ClassVar, NewType, Generic, TypeVar, Type, TypeGuard, Any

from pydantic import validator
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


class ChannelConfiguration(SettingsModel, ABC, Generic[MappingType]):
    description: ChannelName | ChannelSpecialPurpose
    color: Optional[Color] = None
    output_mapping: Optional[MappingType] = None
    delay: float = 0.0

    def has_special_purpose(self) -> bool:
        return isinstance(self.description, ChannelSpecialPurpose)


class DigitalChannelConfiguration(ChannelConfiguration[DigitalMapping]):
    pass


class AnalogChannelConfiguration(ChannelConfiguration[AnalogMapping]):
    pass


class SequencerConfiguration(DeviceConfiguration, ABC):
    time_step: float

    number_channels: ClassVar[int]
    channels: list[ChannelConfiguration]

    @classmethod
    @abstractmethod
    def channel_types(cls) -> list[Type[ChannelConfiguration]]:
        ...

    @validator("channels")
    def validate_channels(cls, channels):
        if len(channels) != cls.number_channels:
            raise ValueError(
                f"The length of channels ({len(channels)}) doesn't match the number of"
                f" channels {cls.number_channels}"
            )
        for channel, channel_type in zip(channels, cls.channel_types()):
            if not isinstance(channel, channel_type):
                raise TypeError(
                    f"Channel {channel} is not of the expected type {channel_type}"
                )
        return channels

from abc import ABC
from collections import Counter
from typing import Optional, ClassVar

import yaml
from pydantic import Field, validator
from pydantic.color import Color

from settings_model import SettingsModel
from units import Quantity
from ..units_mapping import AnalogUnitsMapping

ChannelName = str


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
                f"Cannot construct {cls.__name__} from {node}. "
                f"Expected a scalar node"
            )
        purpose = loader.construct_scalar(node)
        if not isinstance(purpose, str):
            raise ValueError(
                f"Cannot construct {cls.__name__} from {node}. " f"Expected a string"
            )
        return cls(purpose=purpose)

    @classmethod
    def unused(cls):
        return cls(purpose="Unused")


class ChannelConfiguration(SettingsModel, ABC):
    # noinspection PyPropertyDefinition
    number_channels: ClassVar[int]

    channel_descriptions: list[ChannelName | ChannelSpecialPurpose] = Field(
        default_factory=list
    )
    channel_colors: list[Optional[Color]] = Field(default_factory=list)

    @validator("channel_descriptions")
    def validate_channel_descriptions(cls, descriptions):
        if not len(descriptions) == cls.number_channels:
            raise ValueError(
                f"The length of channel descriptions ({len(descriptions)}) doesn't"
                f" match the number of channels {cls.number_channels}"
            )
        counter = Counter(descriptions)
        for description, count in counter.items():
            if not isinstance(description, ChannelSpecialPurpose) and count > 1:
                raise ValueError(f"Channel {description} is specified more than once")
        return descriptions

    @validator("channel_colors")
    def validate_channel_colors(cls, colors):
        if not len(colors) == cls.number_channels:
            raise ValueError(
                f"The length of channel colors ({len(colors)}) doesn't match the"
                f" number of channels {cls.number_channels}"
            )
        else:
            return colors

    def get_named_channels(self) -> set[ChannelName]:
        """Return the names of channels that don't have a special purpose"""
        return {desc for desc in self.channel_descriptions if isinstance(desc, str)}

    def get_channel_index(self, description: ChannelName | ChannelSpecialPurpose):
        if description not in self.channel_descriptions:
            raise ValueError(
                f"Channel '{description}' doesn't exists in the experiment configuration"
            )
        return self.channel_descriptions.index(description)


class DigitalChannelConfiguration(ChannelConfiguration, ABC):
    pass


class AnalogChannelConfiguration(ChannelConfiguration, ABC):
    channel_mappings: list[Optional[AnalogUnitsMapping]] = Field(default_factory=list)

    @validator("channel_mappings")
    def validate_channel_mappings(cls, mappings):
        if not len(mappings) == cls.number_channels:
            raise ValueError(
                f"The length of channel mappings ({len(mappings)}) doesn't match the"
                f" number of channels {cls.number_channels}"
            )
        else:
            return mappings

    def convert_to_output_units(self, channel_name: str, value: Quantity) -> Quantity:
        channel = self.get_channel_index(channel_name)

        if (mapping := self.channel_mappings[channel]) is not None:
            if value.is_compatible_with(mapping.get_input_units()):
                return mapping.convert(value).to(mapping.get_output_units())
            else:
                raise ValueError(
                    f"Incompatible units ({value.units}) for conversion to"
                    f" {mapping.get_input_units()})"
                )
        else:
            raise ValueError(f"No unit mappings defined for channel {channel_name}")

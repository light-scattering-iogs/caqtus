from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import yaml
from appdirs import user_data_dir
from pydantic import Field, validator

from settings_model import SettingsModel
from shot import DigitalLane
from units import Quantity


class ChannelSpecialPurpose(SettingsModel):
    pass


class UnusedChannel(ChannelSpecialPurpose):
    @classmethod
    def representer(cls, dumper: yaml.Dumper, unused: "UnusedChannel"):
        return dumper.represent_scalar(f"!{cls.__name__}", "channel not in use")

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls()


class ReservedChannel(ChannelSpecialPurpose):
    purpose: str

    @classmethod
    @property
    def ni6738_analog_sequencer_variable_clock(cls) -> "ReservedChannel":
        return ReservedChannel(purpose="NI6738_analog_sequencer_variable_clock")


class ChannelColor(SettingsModel):
    red: float
    green: float
    blue: float

    @classmethod
    def representer(cls, dumper: yaml.Dumper, color: "ChannelColor"):
        return dumper.represent_sequence(
            f"!{cls.__name__}",
            [color.red, color.green, color.blue],
        )

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        r, g, b = loader.construct_sequence(node)
        return cls(red=r, green=g, blue=b)


class SpincoreConfig(SettingsModel):
    number_channels: int = Field(24, const=True, exclude=True)
    channel_descriptions: list[str | ChannelSpecialPurpose] = Field(default=[])
    channel_colors: list[Optional[ChannelColor]] = Field(default=[])

    @validator("channel_descriptions")
    def validate_channel_descriptions(cls, descriptions, values):
        descriptions += [
            UnusedChannel()
            for _ in range(0, values["number_channels"] - len(descriptions))
        ]
        return descriptions

    @validator("channel_colors")
    def validate_channel_colors(cls, colors, values):
        colors += [None for _ in range(0, values["number_channels"] - len(colors))]
        return colors

    def find_color(self, lane: DigitalLane) -> Optional[ChannelColor]:
        return self.channel_colors[self.find_channel_index(lane)]

    def find_channel_index(self, lane: DigitalLane):
        return self.channel_descriptions.index(lane.name)

    def get_named_channels(self) -> set[str]:
        """Return the names of channels that don't have a special purpose"""
        return {desc for desc in self.channel_descriptions if isinstance(desc, str)}

    def get_channel_number(self, description: str | ChannelSpecialPurpose):
        return self.channel_descriptions.index(description)


class AnalogUnitsMapping(SettingsModel, ABC):
    @abstractmethod
    def convert(self, input: Quantity) -> Quantity:
        ...

    @property
    @abstractmethod
    def input_dimensionality(self):
        ...

    @property
    @abstractmethod
    def output_dimensionality(self):
        ...


class NI6738AnalogSequencerConfig(SettingsModel):
    number_channels: int = Field(32, const=True, exclude=True)
    channel_descriptions: list[str | ChannelSpecialPurpose] = []
    channel_colors: list[Optional[ChannelColor]] = []
    channel_mappings: list[Optional[AnalogUnitsMapping]] = []
    time_step: float = Field(2.5e-6)

    @validator("channel_descriptions", always=True)
    def validate_channel_descriptions(cls, descriptions, values):
        descriptions += [
            UnusedChannel()
            for _ in range(0, values["number_channels"] - len(descriptions))
        ]
        return descriptions

    @validator("channel_colors", always=True)
    def validate_channel_colors(cls, colors, values):
        colors += [None for _ in range(0, values["number_channels"] - len(colors))]
        return colors

    @validator("channel_mappings", always=True)
    def validate_channel_mappings(cls, mappings, values):
        mappings += [None for _ in range(0, values["number_channels"] - len(mappings))]
        return mappings

    def find_color(self, lane: DigitalLane) -> Optional[ChannelColor]:
        return self.channel_colors[self.find_channel_index(lane)]

    def find_channel_index(self, lane: DigitalLane):
        return self.channel_descriptions.index(lane.name)

    def get_named_channels(self) -> set[str]:
        """Return the names of channels that don't have a special purpose"""
        return {desc for desc in self.channel_descriptions if isinstance(desc, str)}


class ExperimentConfig(SettingsModel):
    data_path: Path = Field(
        default_factory=lambda: Path(user_data_dir("ExperimentControl", "Caqtus"))
        / "data/"
    )
    spincore: SpincoreConfig = Field(default_factory=SpincoreConfig)
    ni6738_analog_sequencer: NI6738AnalogSequencerConfig = Field(
        default_factory=NI6738AnalogSequencerConfig
    )

from enum import Enum, auto
from pathlib import Path
from typing import Optional

import yaml
from appdirs import user_data_dir
from pydantic import Field, validator

from settings_model import SettingsModel, YAMLSerializable
from shot import DigitalLane


class ChannelSpecialPurpose(Enum):
    Unused = auto()
    ReservedForNI6738Sequencer = auto()
    ReservedForOrcaQuestCamera = auto()


YAMLSerializable.register_enum(ChannelSpecialPurpose)


class ChannelColor(SettingsModel):
    red: float
    green: float
    blue: float

    @classmethod
    def representer(cls, dumper: yaml.Dumper, color: "ChannelColor"):
        return dumper.represent_sequence(
            f"!{cls.__name__}", [color.red, color.green, color.blue],
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
            ChannelSpecialPurpose.Unused
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




class ExperimentConfig(SettingsModel):
    data_path: Path = Field(
        default_factory=lambda: Path(user_data_dir("ExperimentControl", "Caqtus"))
        / "data/"
    )
    spincore: SpincoreConfig = Field(default_factory=lambda: SpincoreConfig())

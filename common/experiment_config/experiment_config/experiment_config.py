from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy
import yaml
from PyQt5.QtCore import QSettings
from appdirs import user_config_dir, user_data_dir
from pydantic import Field, validator
from pydantic.color import Color

from sequence import SequenceSteps
from settings_model import SettingsModel
from shot import DigitalLane, AnalogLane
from units import Quantity
from .device_config import DeviceConfiguration


class ChannelSpecialPurpose(SettingsModel):
    purpose: str

    def __hash__(self):
        return hash(self.purpose)

    @classmethod
    def representer(cls, dumper: yaml.Dumper, channel_purpose: "ChannelSpecialPurpose"):
        return dumper.represent_scalar(f"!{cls.__name__}", channel_purpose.purpose)

    @classmethod
    def constructor(cls, loader: yaml.Loader, node: yaml.Node):
        return cls(purpose=loader.construct_scalar(node))

    @classmethod
    def unused(cls):
        return cls(purpose="Unused")


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


class ChannelConfiguration(SettingsModel, ABC):
    @classmethod
    @property
    @abstractmethod
    def number_channels(cls) -> int:
        ...

    channel_descriptions: list[str | ChannelSpecialPurpose] = Field(
        default_factory=list
    )
    channel_colors: list[Optional[Color]] = Field(default_factory=list)

    @validator("channel_descriptions")
    def validate_channel_descriptions(cls, descriptions):
        if not len(descriptions) == cls.number_channels:
            raise ValueError(
                f"The length of channel descriptions ({len(descriptions)}) doesn't match the number of channels "
                f"{cls.number_channels}"
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
                f"The length of channel descriptions ({len(colors)}) doesn't match the number of channels "
                f"{cls.number_channels}"
            )
        else:
            return colors

    def get_named_channels(self) -> set[str]:
        """Return the names of channels that don't have a special purpose"""
        return {desc for desc in self.channel_descriptions if isinstance(desc, str)}

    def get_channel_index(self, description: str | ChannelSpecialPurpose):
        return self.channel_descriptions.index(description)


class SpincoreSequencerConfiguration(DeviceConfiguration, ChannelConfiguration):
    @classmethod
    @property
    def number_channels(cls) -> int:
        return 24

    board_number: int
    time_step: float = Field(
        default=50e-9,
        ge=50e-9,
        units="s",
        description="The quantization time step used when converting step times to instructions.",
    )

    def get_device_type(self) -> str:
        return "SpincorePulseBlaster"

    def get_device_init_args(self) -> dict[str]:
        extra = {
            "board_number": self.board_number,
            "time_step": self.time_step,
        }
        return super().get_device_init_args() | extra


class SpincoreConfig(SettingsModel):
    number_channels: int = Field(24, const=True, exclude=True)
    channel_descriptions: list[str | ChannelSpecialPurpose] = Field(default=[])
    channel_colors: list[Optional[ChannelColor]] = Field(default=[])
    time_step: float = Field(50e-9, units="s")

    @validator("channel_descriptions")
    def validate_channel_descriptions(cls, descriptions, values):
        descriptions += [
            ChannelSpecialPurpose.unused()
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
    def convert(self, input_: Quantity) -> Quantity:
        ...

    @abstractmethod
    def get_input_units(self) -> str:
        ...

    @abstractmethod
    def get_output_units(self) -> str:
        ...


class CalibratedUnitsMapping(AnalogUnitsMapping):
    input_units: str = ""
    output_units: str = "V"
    input_values: list[float] = []
    output_values: list[float] = []

    def get_input_units(self) -> str:
        return self.input_units

    def get_output_units(self) -> str:
        return self.output_units

    def convert(self, input_: Quantity) -> Quantity:
        input_values = numpy.array(self.input_values)
        output_values = numpy.array(self.output_values)
        order = numpy.argsort(input_values)
        sorted_input_values = input_values[order]
        sorted_output_values = output_values[order]
        interp = numpy.interp(
            x=input_.to(self.get_input_units()).magnitude,
            xp=sorted_input_values,
            fp=sorted_output_values,
        )
        min_ = numpy.min(output_values)
        max_ = numpy.max(output_values)
        clipped = numpy.clip(interp, min_, max_)
        return Quantity(clipped, units=self.get_output_units())


class NI6738AnalogSequencerConfig(SettingsModel):
    number_channels: int = Field(32, const=True, exclude=True)
    channel_descriptions: list[str | ChannelSpecialPurpose] = []
    channel_colors: list[Optional[ChannelColor]] = []
    channel_mappings: list[Optional[AnalogUnitsMapping]] = []
    time_step: float = Field(2.5e-6)

    @validator("channel_descriptions", always=True)
    def validate_channel_descriptions(cls, descriptions, values):
        descriptions += [
            ChannelSpecialPurpose.unused()
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

    def find_color(self, lane: AnalogLane) -> Optional[ChannelColor]:
        return self.channel_colors[self.find_channel_index(lane)]

    def find_unit(self, lane_name: str) -> str:
        return self.channel_mappings[
            self.channel_descriptions.index(lane_name)
        ].get_input_units()

    def find_channel_index(self, lane: AnalogLane | str):
        if isinstance(lane, AnalogLane):
            name = lane.name
        else:
            name = lane
        return self.channel_descriptions.index(name)

    def get_named_channels(self) -> set[str]:
        """Return the names of channels that don't have a special purpose"""
        return {desc for desc in self.channel_descriptions if isinstance(desc, str)}

    def convert_values_to_voltages(self, lane_name: str, value: Quantity) -> Quantity:
        lane_index = self.channel_descriptions.index(lane_name)
        if (mapping := self.channel_mappings[lane_index]) is not None:
            if Quantity(1, units=mapping.get_output_units()).is_compatible_with("V"):
                return mapping.convert(value).to("V")
            else:
                raise ValueError(
                    f"Units mapping for lane {lane_name} can't convert {mapping.get_input_units()} to Volt."
                )
        else:
            raise ValueError(
                f"No unit mappings defined for lane {lane_name} to convert {value.units} to Volt"
            )


class ExperimentConfig(SettingsModel):
    data_path: Path = Field(
        default_factory=lambda: Path(user_data_dir("ExperimentControl", "Caqtus"))
        / "data/"
    )
    spincore: SpincoreConfig = Field(default_factory=SpincoreConfig)
    ni6738_analog_sequencer: NI6738AnalogSequencerConfig = Field(
        default_factory=NI6738AnalogSequencerConfig
    )
    header: SequenceSteps = Field(
        default_factory=SequenceSteps,
        description="Steps that are always executed before a sequence",
    )
    device_configurations: list[DeviceConfiguration] = Field(
        default_factory=list,
        description="All the static configurations of the devices present on the experiment.",
    )


def get_config_path() -> Path:
    ui_settings = QSettings("Caqtus", "ExperimentControl")
    config_folder = ui_settings.value(
        "experiment/config_path", user_config_dir("ExperimentControl", "Caqtus")
    )
    config_path = Path(config_folder) / "config.yaml"
    return config_path

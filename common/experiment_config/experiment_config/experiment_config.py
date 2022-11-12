import logging
from pathlib import Path
from typing import Optional

import yaml
from PyQt5.QtCore import QSettings
from appdirs import user_config_dir, user_data_dir
from pydantic import Field, validator
from pydantic.color import Color

from sequence import SequenceSteps
from settings_model import SettingsModel
from shot import AnalogLane
from units import Quantity
from .channel_config import (
    AnalogChannelConfiguration,
    ChannelSpecialPurpose,
    ChannelConfiguration,
    DigitalChannelConfiguration,
)
from .device_config import DeviceConfiguration
from .units_mapping import AnalogUnitsMapping

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


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


class SpincoreSequencerConfiguration(DeviceConfiguration, DigitalChannelConfiguration):
    # noinspection PyPropertyDefinition
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


class NI6738SequencerConfiguration(DeviceConfiguration, AnalogChannelConfiguration):
    device_id: str
    time_step: float = Field(
        default=2.5e-6,
        ge=2.5e-6,
        units="s",
        description="The quantization time step used when converting step times to instructions.",
    )

    @validator("channel_mappings")
    def validate_channel_mappings(cls, channel_mappings):
        channel_mappings: list[
            Optional[AnalogUnitsMapping]
        ] = super().validate_channel_mappings(channel_mappings)
        for channel, mapping in enumerate(channel_mappings):
            if mapping is not None:
                output_units = mapping.get_output_units()
                if not Quantity(1, units=output_units).is_compatible_with("V"):
                    raise ValueError(
                        f"Channel {channel} output units ({output_units}) are not compatible with Volt"
                    )
        return channel_mappings

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    def number_channels(cls) -> int:
        return 32

    def get_device_type(self) -> str:
        return "NI6738AnalogCard"

    def get_device_init_args(self) -> dict[str]:
        extra = {
            "device_id": self.device_id,
            "time_step": self.time_step,
        }
        return super().get_device_init_args() | extra


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

    @validator("device_configurations")
    def validate_device_configurations(
        cls, device_configurations: list[DeviceConfiguration]
    ):
        channel_names = set()
        for device_configuration in device_configurations:
            name = device_configuration.device_name
            if isinstance(device_configuration, ChannelConfiguration):
                device_channel_names = device_configuration.get_named_channels()
                if channel_names.isdisjoint(device_channel_names):
                    channel_names |= device_channel_names
                else:
                    raise ValueError(
                        f"Device {name} has channel names that are already used by an other device: "
                        f"{channel_names & device_channel_names}"
                    )
        return device_configurations

    @property
    def spincore_config(self) -> SpincoreSequencerConfiguration:
        for device_config in self.device_configurations:
            if isinstance(device_config, SpincoreSequencerConfiguration):
                return device_config
        raise ValueError("Could not find a configuration for spincore sequencer")

    @property
    def ni6738_config(self) -> NI6738SequencerConfiguration:
        for device_config in self.device_configurations:
            if isinstance(device_config, NI6738SequencerConfiguration):
                return device_config
        raise ValueError("Could not find a configuration for NI6738 card")

    def find_color(self, channel: str) -> Optional[Color]:
        color = None
        channel_exists = False
        for device_config in self.device_configurations:
            if isinstance(device_config, ChannelConfiguration):
                try:
                    index = device_config.get_channel_index(channel)
                    channel_exists = True
                    color = device_config.channel_colors[index]
                    break
                except ValueError:
                    pass
        if channel_exists:
            return color
        else:
            raise ValueError(f"Channel {channel} doesn't exists in the configuration")

    def get_digital_channels(self) -> set[str]:
        digital_channels = set()
        for device_config in self.device_configurations:
            if isinstance(device_config, DigitalChannelConfiguration):
                digital_channels |= device_config.get_named_channels()
        return digital_channels

    def get_analog_channels(self) -> set[str]:
        analog_channels = set()
        for device_config in self.device_configurations:
            if isinstance(device_config, DigitalChannelConfiguration):
                analog_channels |= device_config.get_named_channels()
        return analog_channels


def get_config_path() -> Path:
    ui_settings = QSettings("Caqtus", "ExperimentControl")
    config_folder = ui_settings.value(
        "experiment/config_path", user_config_dir("ExperimentControl", "Caqtus")
    )
    config_path = Path(config_folder) / "config.yaml"
    return config_path

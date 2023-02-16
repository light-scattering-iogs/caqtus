import copy
import logging
from pathlib import Path
from typing import Optional, Type

from PyQt6.QtCore import QSettings
from appdirs import user_config_dir
from pydantic import Field, validator, PostgresDsn
from pydantic.color import Color

from camera.configuration import CameraConfiguration
from device_config import DeviceConfiguration, DeviceConfigType
from device_config.channel_config import (
    AnalogChannelConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    ChannelSpecialPurpose,
)
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from sequence.configuration import SequenceSteps
from settings_model import SettingsModel
from spincore_sequencer.configuration import SpincoreSequencerConfiguration
from .device_server_config import DeviceServerConfiguration

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentConfig(SettingsModel):
    database_url: PostgresDsn = Field(
        default="postgresql+psycopg2://user:password@host:port/database",
        description="The url to the database where the experiment data will be stored.",
    )
    device_servers: dict[str, DeviceServerConfiguration] = Field(
        default_factory=dict,
        description=(
            "The configurations of the servers that will actually instantiate devices."
        ),
    )
    header: SequenceSteps = Field(
        default_factory=SequenceSteps,
        description=(
            "Steps that are always executed before a sequence. At the moment, it is"
            " only used to pre-define 'constant variables'."
        ),
    )
    device_configurations: list[DeviceConfiguration] = Field(
        default_factory=list,
        description=(
            "All the static configurations of the devices present on the experiment."
        ),
    )

    @classmethod
    def from_file(cls, path):
        with open(path, "r") as file:
            yaml = file.read()
        return cls.from_yaml(yaml)

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
                        f"RuntimeDevice {name} has channel names that are already used"
                        f" by an other device: {channel_names & device_channel_names}"
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

    def get_color(self, channel: str | ChannelSpecialPurpose) -> Optional[Color]:
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

    def get_input_units(self, channel: str) -> Optional[str]:
        units = None
        channel_exists = False
        for device_config in self.device_configurations:
            if isinstance(device_config, AnalogChannelConfiguration):
                try:
                    index = device_config.get_channel_index(channel)
                    channel_exists = True
                except ValueError:
                    pass
                else:
                    if (mapping := device_config.channel_mappings[index]) is not None:
                        units = mapping.get_input_units()
                        break
                    else:
                        raise ValueError(
                            f"Channel {channel} has no defined units mapping"
                        )
        if channel_exists:
            return units
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
            if isinstance(device_config, AnalogChannelConfiguration):
                analog_channels |= device_config.get_named_channels()
        return analog_channels

    def get_cameras(self) -> set[str]:
        cameras = set()
        for device_config in self.device_configurations:
            if isinstance(device_config, CameraConfiguration):
                cameras.add(device_config.device_name)
        return cameras

    def get_device_names(self):
        return (config.device_name for config in self.device_configurations)

    def get_device_configs(
        self, config_type: Type[DeviceConfigType]
    ) -> dict[str, DeviceConfigType]:
        """Return a dictionary of all device configurations matching a given type"""
        return {
            config.device_name: config
            for config in self.device_configurations
            if isinstance(config, config_type)
        }

    def get_device_config(self, device_name: str) -> DeviceConfigType:
        for config in self.device_configurations:
            if config.device_name == device_name:
                return copy.deepcopy(config)
        raise DeviceConfigNotFoundError(f"Could not find a device named {device_name}")

    def set_device_config(self, device_name: str, config: DeviceConfiguration):
        names = [config.device_name for config in self.device_configurations]
        index = names.index(device_name)
        self.device_configurations[index] = copy.deepcopy(config)

    def add_device_config(self, config: DeviceConfiguration):
        if not isinstance(config, DeviceConfiguration):
            raise TypeError(
                f"Trying to create a configuration that is not an instance of"
                f" <DeviceConfiguration>"
            )
        if config.device_name in self.get_device_names():
            raise ValueError(f"Device name {config.device_name} is already being used")
        self.device_configurations.append(config)


def get_config_path() -> Path:
    ui_settings = QSettings("Caqtus", "ExperimentControl")
    config_folder = ui_settings.value(
        "experiment/config_path", user_config_dir("ExperimentControl", "Caqtus")
    )
    config_path = Path(config_folder) / "config.yaml"
    return config_path


class DeviceConfigNotFoundError(RuntimeError):
    pass

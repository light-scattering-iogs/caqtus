import logging
from abc import ABC
from pathlib import Path
from typing import Optional, Type

from PyQt5.QtCore import QSettings
from appdirs import user_config_dir, user_data_dir
from pydantic import Field, validator
from pydantic.color import Color

from camera import ROI
from sequence import SequenceSteps
from settings_model import SettingsModel
from units import Quantity
from .channel_config import (
    AnalogChannelConfiguration,
    ChannelConfiguration,
    DigitalChannelConfiguration,
    ChannelSpecialPurpose,
)
from .device_config import DeviceConfiguration, DeviceConfigType
from .device_server_config import DeviceServerConfiguration
from .units_mapping import AnalogUnitsMapping

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class CameraConfiguration(DeviceConfiguration, ABC):
    roi: ROI

    def get_device_init_args(self) -> dict[str]:
        return super().get_device_init_args() | {
            "roi": self.roi,
            "external_trigger": True,
        }


class OrcaQuestCameraConfiguration(CameraConfiguration):
    camera_number: int

    @classmethod
    def get_device_type(cls) -> str:
        return "OrcaQuestCamera"

    def get_device_init_args(self) -> dict[str]:
        extra = {
            "camera_number": self.camera_number,
        }
        return super().get_device_init_args() | extra


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


class ExperimentConfig(SettingsModel):
    data_path: Path = Field(
        default_factory=lambda: Path(user_data_dir("ExperimentControl", "Caqtus"))
        / "data/"
    )
    device_servers: dict[str, DeviceServerConfiguration] = Field(
        default_factory=dict,
        description="The configurations of the servers that will actually instantiate devices.",
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

    def get_device_configs(
        self, config_type: Type[DeviceConfigType]
    ) -> list[DeviceConfigType]:
        result = []
        for config in self.device_configurations:
            if isinstance(config, config_type):
                result.append(config)
        return result


def get_config_path() -> Path:
    ui_settings = QSettings("Caqtus", "ExperimentControl")
    config_folder = ui_settings.value(
        "experiment/config_path", user_config_dir("ExperimentControl", "Caqtus")
    )
    config_path = Path(config_folder) / "config.yaml"
    return config_path

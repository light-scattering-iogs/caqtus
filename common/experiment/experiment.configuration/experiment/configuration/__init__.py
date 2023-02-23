__version__ = "0.1.0"

from device_config.channel_config import ChannelSpecialPurpose
from orca_quest.configuration import OrcaQuestCameraConfiguration
from siglent_sdg6000x.configuration import SiglentSDG6000XConfiguration
from imaging_source.configuration import ImagingSourceCameraDMK33GR0134Configuration
from .experiment_config import (
    ExperimentConfig,
    DeviceConfigNotFoundError,
    SpincoreSequencerConfiguration,
    NI6738SequencerConfiguration,
    CameraConfiguration,
    DeviceServerConfiguration,
)

device_configs = [
    SpincoreSequencerConfiguration,
    NI6738SequencerConfiguration,
    OrcaQuestCameraConfiguration,
    SiglentSDG6000XConfiguration,
    ImagingSourceCameraDMK33GR0134Configuration,
]

__all__ = [
    ChannelSpecialPurpose,
    ExperimentConfig,
    DeviceConfigNotFoundError,
    CameraConfiguration,
    DeviceServerConfiguration,
    *device_configs,
]

__version__ = "0.1.0"

from device.configuration import DeviceParameter
from device.configuration.channel_config import ChannelSpecialPurpose
from elliptec_ell14.configuration import ElliptecELL14RotationStageConfiguration
from imaging_source.configuration import ImagingSourceCameraDMK33GR0134Configuration
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from orca_quest.configuration import OrcaQuestCameraConfiguration
from spincore_sequencer.configuration import SpincoreSequencerConfiguration
from .experiment_config import (
    ExperimentConfig,
    DeviceConfigNotFoundError,
    CameraConfiguration,
    DeviceServerConfiguration,
)
from .optimization_config import OptimizerConfiguration

device_configs = [
    SpincoreSequencerConfiguration,
    NI6738SequencerConfiguration,
    OrcaQuestCameraConfiguration,
    ImagingSourceCameraDMK33GR0134Configuration,
    ElliptecELL14RotationStageConfiguration,
]

__all__ = [
    ChannelSpecialPurpose,
    ExperimentConfig,
    DeviceConfigNotFoundError,
    CameraConfiguration,
    DeviceServerConfiguration,
    OptimizerConfiguration,
    DeviceParameter,
    *device_configs,
]

__version__ = "0.1.0"

from atom_detector.configuration import AtomDetectorConfiguration
from device.configuration import DeviceParameter
from elliptec_ell14.configuration import ElliptecELL14RotationStageConfiguration
from imaging_source.configuration import ImagingSourceCameraDMK33GR0134Configuration
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from orca_quest.configuration import OrcaQuestCameraConfiguration
from sequencer.configuration import ChannelSpecialPurpose
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
    AtomDetectorConfiguration,
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

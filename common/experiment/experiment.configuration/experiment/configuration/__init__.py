__version__ = "0.1.0"

from aod_tweezer_arranger.configuration import AODTweezerArrangerConfiguration
from atom_detector.configuration import AtomDetectorConfiguration
from device.configuration import DeviceParameter, DeviceConfigurationAttrs
from elliptec_ell14.configuration import ElliptecELL14RotationStageConfiguration
from imaging_source.configuration import ImagingSourceCameraDMK33GR0134Configuration
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from orca_quest.configuration import OrcaQuestCameraConfiguration
from sequencer.configuration import ChannelSpecialPurpose
from spincore_sequencer.configuration import SpincoreSequencerConfiguration
from swabian_pulse_streamer.configuration import SwabianPulseStreamerConfiguration
from tweezer_arranger.configuration import TweezerArrangerConfiguration
from util import serialization
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
    TweezerArrangerConfiguration,
    AODTweezerArrangerConfiguration,
    SwabianPulseStreamerConfiguration,
]


# We can only register the subclasses of DeviceConfiguration for serialization now,
# after all of them have been defined and imported
serialization.include_subclasses(
    DeviceConfigurationAttrs,
    union_strategy=serialization.strategies.include_type(
        tag_name="device_configuration_type"
    ),
)

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

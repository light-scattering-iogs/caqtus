from typing import Any, TypedDict

from atom_detector.configuration import AtomDetectorConfiguration
from atom_detector_lane.configuration import AtomDetectorLane
from camera_lane.configuration import CameraLane
from device.configuration import DeviceName, DeviceParameter
from experiment.configuration import (
    ExperimentConfig,
    SpincoreSequencerConfiguration,
    NI6738SequencerConfiguration,
    CameraConfiguration,
    ElliptecELL14RotationStageConfiguration,
    SwabianPulseStreamerConfiguration,
)
from sequence.configuration import SequenceConfig
from tweezer_arranger.configuration import TweezerArrangerConfiguration
from tweezer_arranger_lane.configuration import TweezerArrangerLane


class InitializationParameters(TypedDict):
    type: str
    server: str
    init_kwargs: dict[DeviceParameter, Any]


def get_devices_initialization_parameters(
    experiment_config: ExperimentConfig, sequence_config: SequenceConfig
) -> dict[DeviceName, InitializationParameters]:
    """Compute the initialization parameters for all devices.

    Returns:
        A dictionary mapping device names to initialization parameters.
    """

    return (
        get_spincore_initialization_parameters(experiment_config, sequence_config)
        | get_swabian_pulse_streamer_initialization_parameters(
            experiment_config, sequence_config
        )
        | get_ni6738_initialization_parameters(experiment_config, sequence_config)
        | get_cameras_initialization_parameters(experiment_config, sequence_config)
        | get_elliptec_initialization_parameters(experiment_config, sequence_config)
        | get_atom_detector_initialization_parameters(
            experiment_config, sequence_config
        )
        | get_tweezer_arranger_initialization_parameters(
            experiment_config, sequence_config
        )
    )


def get_spincore_initialization_parameters(
    experiment_config: ExperimentConfig, _: SequenceConfig
) -> dict[DeviceName, InitializationParameters]:
    """Compute the initialization parameters for all spincore sequencer devices."""

    result = {}
    for name, config in experiment_config.get_device_configs(
        SpincoreSequencerConfiguration
    ).items():
        result[name] = InitializationParameters(
            type=config.get_device_type(),
            server=config.remote_server,
            init_kwargs=config.get_device_init_args(),
        )
    return result


def get_swabian_pulse_streamer_initialization_parameters(
    experiment_config: ExperimentConfig, _: SequenceConfig
) -> dict[DeviceName, InitializationParameters]:

    result = {}

    for name, config in experiment_config.get_device_configs(
        SwabianPulseStreamerConfiguration
    ).items():
        result[name] = InitializationParameters(
            type=config.get_device_type(),
            server=config.remote_server,
            init_kwargs=config.get_device_init_args(),
        )
    return result


def get_ni6738_initialization_parameters(
    experiment_config: ExperimentConfig, _: SequenceConfig
) -> dict[DeviceName, InitializationParameters]:
    """Compute the initialization parameters for all ni6738 cards."""

    result = {}
    for name, config in experiment_config.get_device_configs(
        NI6738SequencerConfiguration
    ).items():
        result[name] = InitializationParameters(
            type=config.get_device_type(),
            server=config.remote_server,
            init_kwargs=config.get_device_init_args(),
        )
    return result


def get_cameras_initialization_parameters(
    experiment_config: ExperimentConfig, sequence_config: SequenceConfig
) -> dict[DeviceName, InitializationParameters]:
    result = {}

    camera_configs = experiment_config.get_device_configs(CameraConfiguration)
    camera_lanes = sequence_config.shot_configurations["shot"].get_lanes(CameraLane)

    for lane_name, camera_lane in camera_lanes.items():
        camera_name = DeviceName(lane_name)
        if camera_name not in camera_configs:
            raise DeviceConfigurationNotFound(
                f"Could not find a camera configuration for the lane {lane_name}"
            )
        camera_config = camera_configs[camera_name]
        init_kwargs = camera_config.get_device_init_args()
        init_kwargs["picture_names"] = camera_lane.get_picture_names()
        init_kwargs["exposures"] = [camera_config.get_default_exposure()] * len(
            init_kwargs["picture_names"]
        )
        result[camera_name] = InitializationParameters(
            type=camera_config.get_device_type(),
            server=camera_config.remote_server,
            init_kwargs=init_kwargs,
        )

    return result


def get_elliptec_initialization_parameters(
    experiment_config: ExperimentConfig, _: SequenceConfig
) -> dict[DeviceName, InitializationParameters]:

    result = {}
    for name, config in experiment_config.get_device_configs(
        ElliptecELL14RotationStageConfiguration
    ).items():
        result[name] = InitializationParameters(
            type=config.get_device_type(),
            server=config.remote_server,
            init_kwargs=config.get_device_init_args(),
        )
    return result


def get_atom_detector_initialization_parameters(
    experiment_config: ExperimentConfig, sequence_config: SequenceConfig
) -> dict[DeviceName, InitializationParameters]:

    result = {}
    atom_detector_lanes = sequence_config.shot_configurations["shot"].get_lanes(
        AtomDetectorLane
    )
    for device_name, device_config in experiment_config.get_device_configs(
        AtomDetectorConfiguration
    ).items():

        if device_name in atom_detector_lanes:
            detector_lane = atom_detector_lanes[device_name]
            result[device_name] = InitializationParameters(
                type=device_config.get_device_type(),
                server=device_config.remote_server,
                init_kwargs=device_config.get_device_init_args(
                    imaging_configurations_to_use=detector_lane.get_imaging_configurations()
                ),
            )
    return result


def get_tweezer_arranger_initialization_parameters(
    experiment_config: ExperimentConfig, sequence_config: SequenceConfig
) -> dict[DeviceName, InitializationParameters]:
    result = {}

    tweezer_arranger_lanes = sequence_config.shot_configurations["shot"].get_lanes(
        TweezerArrangerLane
    )
    for device_name, device_config in experiment_config.get_device_configs(
        TweezerArrangerConfiguration
    ).items():
        if device_name in tweezer_arranger_lanes:
            arranger_lane = tweezer_arranger_lanes[device_name]
            result[device_name] = InitializationParameters(
                type=device_config.get_device_type(),
                server=device_config.remote_server,
                init_kwargs=device_config.get_device_init_args(
                    tweezer_configurations_to_use=arranger_lane.get_static_configurations(),
                    tweezer_sequence=arranger_lane.list_steps(),
                ),
            )
    return result


class DeviceConfigurationNotFound(Exception):
    pass

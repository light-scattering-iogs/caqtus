from typing import Any, TypedDict

from experiment.configuration import (
    ExperimentConfig,
    SpincoreSequencerConfiguration,
    NI6738SequencerConfiguration,
    CameraConfiguration,
    ElliptecELL14RotationStageConfiguration,
)
from sequence.configuration import SequenceConfig, CameraLane


class InitializationParameters(TypedDict):
    type: str
    server: str
    init_kwargs: dict[str, Any]


def get_devices_initialization_parameters(
    experiment_config: ExperimentConfig, sequence_config: SequenceConfig
) -> dict[str, InitializationParameters]:
    """Compute the initialization parameters for all devices.

    Returns:
        A dictionary mapping device names to initialization parameters.
    """

    return (
        get_spincore_initialization_parameters(experiment_config, sequence_config)
        | get_ni6738_initialization_parameters(experiment_config, sequence_config)
        | get_cameras_initialization_parameters(experiment_config, sequence_config)
        | get_elliptec_initialization_parameters(experiment_config, sequence_config)
    )


def get_spincore_initialization_parameters(
    experiment_config: ExperimentConfig, sequence_config: SequenceConfig
) -> dict[str, InitializationParameters]:
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


def get_ni6738_initialization_parameters(
    experiment_config: ExperimentConfig, sequence_config: SequenceConfig
) -> dict[str, InitializationParameters]:
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
) -> dict[str, InitializationParameters]:
    result = {}

    camera_configs = experiment_config.get_device_configs(CameraConfiguration)
    camera_lanes = sequence_config.shot_configurations["shot"].get_lanes(CameraLane)

    for camera_name, camera_lane in camera_lanes.items():
        if camera_name not in camera_configs:
            raise DeviceConfigurationNotFound(
                f"Could not find a camera configuration for the lane {camera_name}"
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
    experiment_config: ExperimentConfig, sequence_config: SequenceConfig
) -> dict[str, InitializationParameters]:

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


class DeviceConfigurationNotFound(Exception):
    pass

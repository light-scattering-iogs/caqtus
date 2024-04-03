import logging
from collections.abc import Mapping
from typing import TypeVar, Any

from caqtus.device import (
    DeviceName,
    DeviceConfiguration,
    DeviceParameter,
    get_configurations_by_type,
)
from caqtus.device.camera import CameraConfiguration
from caqtus.session.shot import TimeLanes, TimeLane
from caqtus.session.shot.timelane import CameraTimeLane
from .camera_parameter_compiler import CamerasParameterCompiler
from .sequencer_paramer_compiler import SequencerParameterCompiler
from .shot_compiler import ShotCompiler
from .variable_namespace import VariableNamespace

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DefaultShotCompiler(ShotCompiler):
    """Default shot compiler.

    This is a shot compiler that computes shot parameters for cameras and sequencers.
    """

    def __init__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfiguration],
    ):
        self.camera_compiler = CamerasParameterCompiler(
            shot_timelanes.step_names,
            shot_timelanes.step_durations,
            get_lanes_with_type(shot_timelanes.lanes, CameraTimeLane),
            get_configurations_by_type(device_configurations, CameraConfiguration),
        )

        self.sequencers_compiler = SequencerParameterCompiler(
            shot_timelanes.step_names,
            shot_timelanes.step_durations,
            shot_timelanes.lanes,
            device_configurations,
        )

    def compile_shot(
        self, shot_parameters: VariableNamespace
    ) -> Mapping[DeviceName, Mapping[DeviceParameter, Any]]:
        result = {}
        result.update(self.camera_compiler.compile(shot_parameters))
        result.update(self.sequencers_compiler.compile(shot_parameters))
        return result


_L = TypeVar("_L", bound=TimeLane)


def get_lanes_with_type(
    lanes: Mapping[str, TimeLane], lane_type: type[_L]
) -> Mapping[str, _L]:
    return {name: lane for name, lane in lanes.items() if isinstance(lane, lane_type)}


_D = TypeVar("_D", bound=DeviceConfiguration)


def get_device_configurations_with_type(
    device_configurations: Mapping[DeviceName, DeviceConfiguration],
    device_type: type[_D],
) -> Mapping[DeviceName, _D]:
    return {
        name: configuration
        for name, configuration in device_configurations.items()
        if isinstance(configuration, device_type)
    }

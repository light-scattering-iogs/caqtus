from collections.abc import Mapping
from typing import TypeVar, Any

from core.device import DeviceName, DeviceConfigurationAttrs, DeviceParameter
from core.device.camera import CameraConfiguration
from core.session.shot import TimeLanes, TimeLane
from core.session.shot.timelane import CameraTimeLane
from .camera_parameter_compiler import CamerasParameterCompiler
from .shot_compiler import ShotCompiler
from .variable_namespace import VariableNamespace


class DefaultShotCompiler(ShotCompiler):
    """Default shot compiler.

    This is a shot compiler that computes shot parameters for cameras and sequencers.
    """

    def __init__(
        self,
        shot_timelanes: TimeLanes,
        device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    ):
        self.camera_compiler = CamerasParameterCompiler(
            shot_timelanes.step_names,
            shot_timelanes.step_durations,
            get_lanes_with_type(shot_timelanes.lanes, CameraTimeLane),
            get_device_configurations_with_type(
                device_configurations, CameraConfiguration
            ),
        )

    def compile_shot(
        self, shot_parameters: VariableNamespace
    ) -> Mapping[DeviceName, Mapping[DeviceParameter, Any]]:
        result = {}
        result.update(self.camera_compiler.compile(shot_parameters))
        return result


_L = TypeVar("_L", bound=TimeLane)


def get_lanes_with_type(
    lanes: Mapping[str, TimeLane], lane_type: type[_L]
) -> Mapping[str, _L]:
    return {name: lane for name, lane in lanes.items() if isinstance(lane, lane_type)}


_D = TypeVar("_D", bound=DeviceConfigurationAttrs)


def get_device_configurations_with_type(
    device_configurations: Mapping[DeviceName, DeviceConfigurationAttrs],
    device_type: type[_D],
) -> Mapping[DeviceName, _D]:
    return {
        name: configuration
        for name, configuration in device_configurations.items()
        if isinstance(configuration, device_type)
    }

from collections.abc import Mapping
from typing import Any

from core.device import DeviceName, DeviceParameter
from core.device.camera import CameraConfiguration
from core.session.shot import CameraTimeLane


def get_cameras_initialization_parameters(
    camera_configs: Mapping[DeviceName, CameraConfiguration],
    camera_lanes: Mapping[str, CameraTimeLane],
) -> dict[DeviceName, dict[DeviceParameter, Any]]:
    result = {}

    for lane_name, camera_lane in camera_lanes.items():
        camera_name = DeviceName(lane_name)
        if camera_name not in camera_configs:
            raise ValueError(
                f"Could not find a camera configuration for the lane {lane_name}"
            )
        camera_config = camera_configs[camera_name]
        init_kwargs = camera_config.get_device_init_args()
        result[camera_name] = init_kwargs

    return result

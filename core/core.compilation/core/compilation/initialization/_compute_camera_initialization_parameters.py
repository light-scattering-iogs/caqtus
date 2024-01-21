from collections.abc import Mapping
from typing import assert_never, Any

from core.device import DeviceName, DeviceParameter
from core.device.camera import CameraConfiguration
from core.session.shot import CameraTimeLane
from core.session.shot.timelane import TakePicture


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
        picture_names = get_picture_names(camera_lane)
        init_kwargs[DeviceParameter("picture_names")] = get_picture_names(camera_lane)
        init_kwargs[DeviceParameter("exposures")] = [
            camera_config.get_default_exposure()
        ] * len(picture_names)
        result[camera_name] = init_kwargs

    return result


def get_picture_names(lane: CameraTimeLane) -> list[str]:
    result = []
    for block_value in lane.values():
        if isinstance(block_value, TakePicture):
            result.append(block_value.picture_name)
        elif block_value is None:
            pass
        else:
            assert_never(block_value)
    return result

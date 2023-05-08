from typing import Any

from camera.configuration import CameraConfiguration
from device.configuration import DeviceParameter


class OrcaQuestCameraConfiguration(CameraConfiguration):
    """Holds the configuration for an OrcaQuest camera.

    Attributes:
        camera_number: The number of the camera to use.
    """

    camera_number: int

    @classmethod
    def get_device_type(cls) -> str:
        return "OrcaQuestCamera"

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        extra = {
            "camera_number": self.camera_number,
            "timeout": 1,
        }
        return super().get_device_init_args() | extra

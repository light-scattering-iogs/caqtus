from abc import ABC
from typing import Any

from device.configuration import DeviceConfiguration, DeviceParameter
from roi import RectangularROI


class CameraConfiguration(DeviceConfiguration, ABC):
    """Contains static information to initialize a camera.

    This class is meant to be subclassed to add device-specific attributes.

    Attributes:
        roi: The region of interest to keep from the image taken by the camera.
    """

    roi: RectangularROI

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        return super().get_device_init_args() | {
            "roi": self.roi,
            "external_trigger": True,
        }

    @staticmethod
    def get_default_exposure() -> float:
        return 1e-3

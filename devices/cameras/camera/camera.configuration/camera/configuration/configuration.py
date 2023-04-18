from abc import ABC

from device_config import DeviceConfiguration
from .camera_roi import ROI


class CameraConfiguration(DeviceConfiguration, ABC):
    """Contains static information to initialize a camera.

    This class is meant to be subclassed to add device-specific attributes.

    Attributes:
        roi: The region of interest to keep from the image taken by the camera.
    """

    roi: ROI

    def get_device_init_args(self) -> dict[str]:
        return super().get_device_init_args() | {
            "roi": self.roi,
            "external_trigger": True,
        }

    @staticmethod
    def get_default_exposure() -> float:
        return 1e-3

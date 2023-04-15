from abc import ABC

from pydantic import Field

from device_config import DeviceConfiguration
from settings_model import SettingsModel


class CameraConfiguration(DeviceConfiguration, ABC):
    """Contains static information to initialize a camera.

    This class is meant to be subclassed to add device-specific attributes.

    Attributes:
        roi: The region of interest to keep from the image taken by the camera.
    """

    roi: "ROI"

    def get_device_init_args(self) -> dict[str]:
        return super().get_device_init_args() | {
            "roi": self.roi,
            "external_trigger": True,
        }

    @staticmethod
    def get_default_exposure() -> float:
        return 1e-3


class ROI(SettingsModel):
    x: int = Field(
        description="horizontal coordinate of the corner of the roi",
    )
    width: int = Field(description="width of the roi")
    y: int = Field(description="x coordinate of the corner of the roi")
    height: int = Field(description="height of the roi")


CameraConfiguration.update_forward_refs()

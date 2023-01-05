from abc import ABC

from pydantic import Field

from device_config import DeviceConfiguration
from settings_model import SettingsModel


class CameraConfiguration(DeviceConfiguration, ABC):
    roi: "ROI"

    def get_device_init_args(self) -> dict[str]:
        return super().get_device_init_args() | {
            "roi": self.roi,
            "external_trigger": True,
        }


class ROI(SettingsModel):
    x: int = Field(
        description="horizontal coordinate of the corner of the roi",
    )
    width: int = Field(description="width of the roi")
    y: int = Field(description="x coordinate of the corner of the roi")
    height: int = Field(description="height of the roi")


CameraConfiguration.update_forward_refs()

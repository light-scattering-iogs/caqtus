from abc import ABC
from typing import Literal

from pydantic import Field

from camera.configuration import CameraConfiguration


class ImagingSourceCameraConfiguration(CameraConfiguration, ABC):

    camera_name: str = Field(description="The name of the camera")
    format: Literal["Y16", "Y800"]

    def get_device_init_args(self) -> dict[str]:
        extra = {
            "camera_name": self.camera_name,
            "format": self.format,
        }
        return super().get_device_init_args() | extra


class ImagingSourceCameraDMK33GR0134Configuration(ImagingSourceCameraConfiguration):
    @classmethod
    def get_device_type(cls) -> str:
        return "ImagingSourceCameraDMK33GR0134"

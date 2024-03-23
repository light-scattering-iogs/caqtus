from __future__ import annotations

from typing import Any, Literal

import attrs
from caqtus.device import DeviceParameter
from caqtus.device.camera.configuration import CameraConfiguration
from caqtus.utils import serialization


@attrs.define
class ImagingSourceCameraConfiguration(CameraConfiguration):
    """Holds the configuration for a camera from The Imaging Source.

    Attributes:
        camera_name: The name of the camera to use.
    """

    camera_name: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    format: Literal["Y16", "Y800"] = attrs.field(
        validator=attrs.validators.in_(["Y16", "Y800"]),
        on_setattr=attrs.setters.validate,
    )

    @classmethod
    def get_device_type(cls) -> str:
        return "ImagingSourceCameraDMK33GR0134"

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        extra = {
            DeviceParameter("camera_name"): self.camera_name,
            DeviceParameter("format"): self.format,
            DeviceParameter("timeout"): 1,
        }
        return super().get_device_init_args() | extra

    @classmethod
    def dump(cls, config: ImagingSourceCameraConfiguration) -> serialization.JSON:
        return serialization.unstructure(config)

    @classmethod
    def load(cls, data: serialization.JSON) -> ImagingSourceCameraConfiguration:
        return serialization.structure(data, ImagingSourceCameraConfiguration)

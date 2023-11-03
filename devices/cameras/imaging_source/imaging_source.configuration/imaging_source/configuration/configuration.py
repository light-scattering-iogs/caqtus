from abc import ABC
from typing import Literal, Any

from camera.configuration import CameraConfiguration
from device.configuration import DeviceParameter
from settings_model import YAMLSerializable
from util import attrs


@attrs.define(slots=False)
class ImagingSourceCameraConfiguration(CameraConfiguration, ABC):
    camera_name: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    format: Literal["Y16", "Y800"] = attrs.field(
        converter=str,
        validator=attrs.validators.in_({"Y16", "Y800"}),
        on_setattr=attrs.setters.pipe(attrs.setters.convert, attrs.setters.validate),
    )

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        extra = {
            DeviceParameter("camera_name"): self.camera_name,
            DeviceParameter("format"): self.format,
            DeviceParameter("timeout"): 1,
        }
        return super().get_device_init_args() | extra


class ImagingSourceCameraDMK33GR0134Configuration(ImagingSourceCameraConfiguration):
    @classmethod
    def get_device_type(cls) -> str:
        return "ImagingSourceCameraDMK33GR0134"


YAMLSerializable.register_attrs_class(ImagingSourceCameraDMK33GR0134Configuration)

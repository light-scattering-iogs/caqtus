from __future__ import annotations

from typing import Literal, TYPE_CHECKING

import attrs

from caqtus.device import DeviceName
from caqtus.device.camera import CameraConfiguration, CameraUpdateParams
from caqtus.shot_compilation import ShotContext
from caqtus.utils import serialization

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from ..runtime import ImagingSourceCameraDMK33GR0134


@attrs.define
class ImagingSourceCameraConfiguration(
    CameraConfiguration["ImagingSourceCameraDMK33GR0134"]
):
    """Holds the configuration for a camera from The Imaging Source.

    Attributes:
        camera_name: The name of the camera to use.
            This is written on the camera.
        format: The format of the camera.
            Can be "Y16" or "Y800" respectively for 16-bit and 8-bit monochrome images.
    """

    camera_name: str = attrs.field(converter=str, on_setattr=attrs.setters.convert)
    format: Literal["Y16", "Y800"] = attrs.field(
        validator=attrs.validators.in_(["Y16", "Y800"]),
        on_setattr=attrs.setters.validate,
    )

    def get_device_initialization_method(self, device_name, sequence_context):
        return (
            super()
            .get_device_initialization_method(device_name, sequence_context)
            .with_extra_parameters(
                name=device_name,
                camera_name=self.camera_name,
                format=self.format,
                timeout=1,
            )
        )

    def compile_device_shot_parameters(
        self,
        device_name: DeviceName,
        shot_context: ShotContext,
    ) -> CameraUpdateParams:
        return super().compile_device_shot_parameters(device_name, shot_context)

    @classmethod
    def dump(cls, config: ImagingSourceCameraConfiguration) -> serialization.JSON:
        return serialization.unstructure(config)

    @classmethod
    def load(cls, data: serialization.JSON) -> ImagingSourceCameraConfiguration:
        return serialization.structure(data, ImagingSourceCameraConfiguration)

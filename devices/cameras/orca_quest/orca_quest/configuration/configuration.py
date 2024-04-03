from __future__ import annotations

from typing import Any

import attrs

from caqtus.device import DeviceParameter
from caqtus.device.camera import CameraConfiguration
from caqtus.utils import serialization


@attrs.define
class OrcaQuestCameraConfiguration(CameraConfiguration):
    """Holds the configuration for an OrcaQuest camera.

    Attributes:
        camera_number: The number of the camera to use.
    """

    camera_number: int = attrs.field(converter=int, on_setattr=attrs.setters.convert)

    @classmethod
    def get_device_type(cls) -> str:
        return "OrcaQuestCamera"

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        extra = {
            DeviceParameter("camera_number"): self.camera_number,
            DeviceParameter("timeout"): 1,
        }
        return super().get_device_init_args() | extra

    @classmethod
    def dump(cls, config: OrcaQuestCameraConfiguration) -> serialization.JSON:
        return serialization.unstructure(config)

    @classmethod
    def load(cls, data: serialization.JSON) -> OrcaQuestCameraConfiguration:
        return serialization.structure(data, OrcaQuestCameraConfiguration)

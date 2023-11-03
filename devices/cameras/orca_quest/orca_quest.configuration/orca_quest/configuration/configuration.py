from typing import Any

from camera.configuration import CameraConfiguration
from device.configuration import DeviceParameter
from settings_model import YAMLSerializable
from util import attrs


@attrs.define(slots=False)
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


YAMLSerializable.register_attrs_class(OrcaQuestCameraConfiguration)

from abc import ABC
from typing import Any

from device.configuration import DeviceConfigurationAttrs, DeviceParameter
from roi import RectangularROI
from util import attrs


@attrs.define(slots=False)
class CameraConfiguration(DeviceConfigurationAttrs, ABC):
    """Contains static information to initialize a camera.

    This class is meant to be subclassed to add device-specific attributes.

    Attributes:
        roi: The region of interest to keep from the image taken by the camera.
    """

    roi: RectangularROI = attrs.field(
        validator=attrs.validators.instance_of(RectangularROI),
        on_setattr=attrs.setters.validate,
    )

    def get_device_init_args(self) -> dict[DeviceParameter, Any]:
        return super().get_device_init_args() | {
            DeviceParameter("roi"): self.roi,
            DeviceParameter("external_trigger"): True,
        }

    @staticmethod
    def get_default_exposure() -> float:
        return 1e-3

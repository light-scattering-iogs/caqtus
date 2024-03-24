from abc import ABC
from typing import Any

import attrs
from caqtus.utils.roi import RectangularROI
from ..configuration import DeviceConfigurationAttrs, DeviceParameter


@attrs.define
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

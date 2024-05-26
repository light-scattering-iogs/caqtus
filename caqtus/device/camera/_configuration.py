from typing import TypeVar, Generic

import attrs

from caqtus.utils.roi import RectangularROI
from ._controller import CameraController
from ._runtime import Camera
from ..configuration import DeviceConfiguration

CameraType = TypeVar("CameraType", bound=Camera)


@attrs.define
class CameraConfiguration(
    DeviceConfiguration[CameraType], Generic[CameraType]
):
    """Contains the necessary information about a camera.

    Attributes:
        roi: The region of interest to keep from the image taken by the camera.
    """

    roi: RectangularROI = attrs.field(
        validator=attrs.validators.instance_of(RectangularROI),
        on_setattr=attrs.setters.validate,
    )

    def get_controller_type(self):
        return CameraController

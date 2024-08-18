from typing import TypeVar

import attrs

from caqtus.types.image.roi import RectangularROI
from ._runtime import Camera
from ..configuration import DeviceConfiguration


@attrs.define
class CameraConfiguration[C: Camera](DeviceConfiguration[C]):
    """Contains the necessary information about a camera.

    Attributes:
        roi: The region of interest to keep for the images taken by the camera for all
            acquisitions.
    """

    roi: RectangularROI = attrs.field(
        validator=attrs.validators.instance_of(RectangularROI),
        on_setattr=attrs.setters.validate,
    )


CameraConfigurationType = TypeVar("CameraConfigurationType", bound=CameraConfiguration)

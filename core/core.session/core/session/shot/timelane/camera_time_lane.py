import attrs

from core.types.image import ImageLabel
from .timelane import TimeLane


@attrs.define
class TakePicture:
    picture_name: ImageLabel


@attrs.define(eq=False, repr=False)
class CameraTimeLane(TimeLane[TakePicture | None]):
    pass

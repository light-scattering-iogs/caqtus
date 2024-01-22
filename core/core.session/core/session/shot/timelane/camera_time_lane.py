import attrs

from core.types.image import ImageLabel
from util import serialization
from .timelane import TimeLane


@attrs.define
class TakePicture:
    picture_name: ImageLabel


@attrs.define(init=False, eq=False, repr=False)
class CameraTimeLane(TimeLane[TakePicture | None]):
    pass


def unstructure_hook(lane: CameraTimeLane):
    return {
        "spanned_values": serialization.unstructure(
            lane._spanned_values, list[tuple[TakePicture | None, int]]
        )
    }


def structure_hook(data, _) -> CameraTimeLane:
    structured = serialization.structure(
        data["spanned_values"], list[tuple[TakePicture | None, int]]
    )
    return CameraTimeLane.from_spanned_values(structured)


serialization.register_structure_hook(CameraTimeLane, structure_hook)
serialization.register_unstructure_hook(CameraTimeLane, unstructure_hook)

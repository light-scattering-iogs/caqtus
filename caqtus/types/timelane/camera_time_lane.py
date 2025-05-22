import attrs

from caqtus.types.image import ImageLabel
from caqtus.utils import serialization
from .timelane import TimeLane, Span


@attrs.define
class TakePicture:
    picture_name: ImageLabel


@attrs.define(init=False, eq=False, repr=False)
class CameraTimeLane(TimeLane[TakePicture | None]):
    def get_picture_labels(self) -> list[ImageLabel]:
        return [
            picture.picture_name
            for picture in self.block_values()
            if isinstance(picture, TakePicture)
        ]


def unstructure_hook(lane: CameraTimeLane):
    return {
        "spanned_values": serialization.unstructure(
            lane._spanned_values, list[tuple[TakePicture | None, int]]
        )
    }


def structure_hook(data, _) -> CameraTimeLane:
    structured = serialization.structure(
        data["spanned_values"], list[tuple[TakePicture | None, Span]]
    )
    return CameraTimeLane.from_spanned_values(structured)


serialization.register_structure_hook(CameraTimeLane, structure_hook)
serialization.register_unstructure_hook(CameraTimeLane, unstructure_hook)

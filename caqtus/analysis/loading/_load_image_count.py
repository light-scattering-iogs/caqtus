from __future__ import annotations

from typing import Optional, Any

import attrs
import numpy as np
import polars

from caqtus.session import Shot
from caqtus.types.image import ImageLabel, is_image
from caqtus.types.image.roi import ROI, RectangularROI
from ._combinable_importers import CombinableLoader
from ...types.data import DataLabel
from ...types.recoverable_exceptions import InvalidTypeError


@attrs.define
class LoadImageCount(CombinableLoader):
    """Loads the count values of an image.

    This loader computes the sum of the pixel values of an image.

    Args:
        camera_name: The name of the camera.
        picture_name: The name of the picture.
        background_name: The name of the background picture to subtract before computing
            the sum. If None, no background is subtracted.
        roi: The region of interest to reduce the sum to.
            If None, the whole picture is used.
        column_name: The name of the column to store the computed sum in.
            If not provided, the column is named '{picture_name} count'.
    """

    camera_name: str
    picture_name: ImageLabel
    background_name: Optional[ImageLabel] = None
    roi: Optional[ROI] = None
    column_name: Optional[str] = None

    _indices: Any = attrs.field(init=False, default=None)
    _image_data_label: str = attrs.field(init=False, default=None)
    _background_data_label: Optional[str] = attrs.field(init=False, default=None)

    def __attrs_post_init__(self):
        self._column_name = self.column_name or f"{self.picture_name} count"
        self._image_data_label = rf"{self.camera_name}\{self.picture_name}"
        if self.background_name is not None:
            self._background_data_label = rf"{self.camera_name}\{self.background_name}"
        match self.roi:
            case None:
                self._indices = (slice(None), slice(None))
            case RectangularROI() as rectangular_roi:
                self._indices = (
                    slice(rectangular_roi.x, rectangular_roi.x + rectangular_roi.width),
                    slice(
                        rectangular_roi.y, rectangular_roi.y + rectangular_roi.height
                    ),
                )
            case _:
                self._indices = self.roi.get_indices()

    def load(self, shot: Shot) -> polars.DataFrame:
        image = shot.get_data_by_label(DataLabel(self._image_data_label))
        if not is_image(image):
            raise InvalidTypeError(
                f"Expected data '{self._image_data_label}' to be an image, got {image} "
                f"instead"
            )

        image = image[self._indices]

        picture_count = np.sum(image)
        if self._background_data_label is None:
            background_count = 0
        else:
            background = shot.get_data_by_label(DataLabel(self._background_data_label))
            if not is_image(background):
                raise InvalidTypeError(
                    f"Expected data '{self._background_data_label}' to be an image, "
                    f"got {background} instead"
                )
            background_count = np.sum(background)

        count = picture_count - background_count
        return polars.DataFrame(polars.Series(self._column_name, [count]))

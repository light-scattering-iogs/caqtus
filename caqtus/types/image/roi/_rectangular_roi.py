from collections.abc import Iterable

import attrs
import numpy as np

from ._roi import ROI


@attrs.define
class RectangularROI(ROI):
    """Rectangular region of interest inside an image.

    Attributes:
        x: Horizontal coordinate of the left column of the roi, in pixels.
        width: Number of columns in the roi.
        y: Vertical coordinate of the bottom row of the roi, in pixels.
        height: Number of rows in the roi.
    """

    x: int = attrs.field(
        validator=[attrs.validators.instance_of(int), attrs.validators.ge(0)],
        on_setattr=attrs.setters.validate,
    )
    width: int = attrs.field(
        validator=[attrs.validators.instance_of(int), attrs.validators.ge(0)],
        on_setattr=attrs.setters.validate,
    )
    y: int = attrs.field(
        validator=[attrs.validators.instance_of(int), attrs.validators.ge(0)],
        on_setattr=attrs.setters.validate,
    )
    height: int = attrs.field(
        validator=[attrs.validators.instance_of(int), attrs.validators.ge(0)],
        on_setattr=attrs.setters.validate,
    )

    @x.validator  # type: ignore
    def _validate_x(self, _, x):
        if x >= self.original_image_size[0]:
            raise ValueError("x must be smaller than original_width")

    @width.validator  # type: ignore
    def _validate_width(self, _, width):
        if self.x + width > self.original_image_size[0]:
            raise ValueError("x + width must be smaller than original_width")

    @y.validator  # type: ignore
    def _validate_y(self, _, y):
        if y >= self.original_image_size[1]:
            raise ValueError("y must be smaller than original_height")

    @height.validator  # type: ignore
    def _validate_height(self, _, height):
        if self.y + height > self.original_image_size[1]:
            raise ValueError("y + height must be smaller than original_height")

    def get_mask(self) -> np.ndarray:
        """A boolean array with the same shape as the original image.

        True values indicate that the pixel is part of the region of interest."""

        mask = np.full(self.original_image_size, False)
        mask[self.y : self.y + self.height, self.x : self.x + self.width] = True
        return mask

    def get_indices(self) -> tuple[Iterable[int], Iterable[int]]:
        """Return the pixels in the original image that are part of the ROI."""

        raise NotImplementedError

    @property
    def left(self) -> int:
        """Return the left column (included) of the roi."""

        return self.x

    @property
    def right(self) -> int:
        """Return the right column (included) of the roi."""

        return self.x + self.width - 1

    @property
    def bottom(self) -> int:
        """Return the bottom row (included) of the roi."""

        return self.y

    @property
    def top(self) -> int:
        """Return the top row (included) of the roi."""

        return self.y + self.height - 1

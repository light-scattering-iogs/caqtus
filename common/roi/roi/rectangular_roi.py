import numpy as np

from settings_model import YAMLSerializable
from util import attrs
from .roi import ROI


@attrs.define(slots=False)
class RectangularROI(ROI):
    """Rectangular region of interest inside an image.

    Attributes:
        x: horizontal coordinate of the left column of the roi.
        width: width of the roi.
        y: vertical coordinate of the bottom row of the roi.
        height: height of the roi.
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

    @x.validator
    def _validate_x(self, _, x):
        if x >= self.original_image_size[0]:
            raise ValueError("x must be smaller than original_width")
        return x

    @width.validator
    def _validate_width(self, _, width):
        if self.x + width > self.original_image_size[0]:
            raise ValueError("x + width must be smaller than original_width")
        return width

    @y.validator
    def _validate_y(self, _, y):
        if y >= self.original_image_size[1]:
            raise ValueError("y must be smaller than original_height")
        return y

    @height.validator
    def _validate_height(self, _, height):
        if self.y + height > self.original_image_size[1]:
            raise ValueError("y + height must be smaller than original_height")
        return height

    def get_mask(self) -> np.ndarray:
        """A boolean array with the same shape as the original image.

        True values indicate that the pixel is part of the region of interest."""

        mask = np.full(self.original_image_size, False)
        mask[self.y : self.y + self.height, self.x : self.x + self.width] = True
        return mask

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


YAMLSerializable.register_attrs_class(RectangularROI)

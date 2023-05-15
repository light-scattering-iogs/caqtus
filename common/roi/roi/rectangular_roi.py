import numpy as np
from pydantic import validator, Field

from .roi import ROI


class RectangularROI(ROI):
    """Rectangular region of interest inside an image.

    Attributes:
        x: horizontal coordinate of the left column of the roi.
        width: width of the roi.
        y: vertical coordinate of the bottom row of the roi.
        height: height of the roi.
    """

    x: int = Field(..., ge=0)
    width: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    height: int = Field(..., ge=0)

    @property
    def mask(self) -> np.ndarray:
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

    @validator("x")
    def _validate_x(cls, x, values):
        if "original_image_size" not in values:
            raise ValueError("original_image_size is not defined")
        if x >= values["original_image_size"][0]:
            raise ValueError("x must be smaller than original_width")
        return x

    @validator("width")
    def _validate_width(cls, width, values):
        if "original_image_size" not in values:
            raise ValueError("original_image_size is not defined")
        if "x" not in values:
            raise ValueError("x is not defined")
        if values["x"] + width > values["original_image_size"][0]:
            raise ValueError("x + width must be smaller than original_width")
        return width

    @validator("y")
    def _validate_y(cls, y, values):
        if "original_image_size" not in values:
            raise ValueError("original_image_size is not defined")
        if y >= values["original_image_size"][1]:
            raise ValueError("y must be smaller than original_height")
        return y

    @validator("height")
    def _validate_height(cls, height, values):
        if "original_image_size" not in values:
            raise ValueError("original_image_size is not defined")
        if "y" not in values:
            raise ValueError("y is not defined")
        if values["y"] + height > values["original_image_size"][1]:
            raise ValueError("y + height must be smaller than original_height")
        return height

from pydantic import Field, validator

from settings_model import SettingsModel


class ROI(SettingsModel):
    """Rectangular region of interest inside an image.

    Attributes:
        original_width: width of the original image.
        original_height: height of the original image.
        x: horizontal coordinate of the left column of the roi.
        width: width of the roi.
        y: vertical coordinate of the bottom row of the roi.
        height: height of the roi.
    """

    original_width: int = Field(..., ge=0)
    original_height: int = Field(..., ge=0)
    x: int = Field(..., ge=0)
    width: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    height: int = Field(..., ge=0)

    @validator("x")
    def validate_x(cls, x, values):
        if "original_width" not in values:
            raise ValueError("original_width is not defined")
        if x >= values["original_width"]:
            raise ValueError("x must be smaller than original_width")
        return x

    @validator("width")
    def validate_width(cls, width, values):
        if "original_width" not in values:
            raise ValueError("original_width is not defined")
        if "x" not in values:
            raise ValueError("x is not defined")
        if values["x"] + width > values["original_width"]:
            raise ValueError("x + width must be smaller than original_width")
        return width

    @validator("y")
    def validate_y(cls, y, values):
        if "original_height" not in values:
            raise ValueError("original_height is not defined")
        if y >= values["original_height"]:
            raise ValueError("y must be smaller than original_height")
        return y

    @validator("height")
    def validate_height(cls, height, values):
        if "original_height" not in values:
            raise ValueError("original_height is not defined")
        if "y" not in values:
            raise ValueError("y is not defined")
        if values["y"] + height > values["original_height"]:
            raise ValueError("y + height must be smaller than original_height")
        return height

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

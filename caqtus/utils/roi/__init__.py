import warnings

from caqtus.types.image import (
    Width,
    Height,
    ArbitraryROI,
    RectangularROI,
    RotatedRectangularROI,
    ROI,
)

warnings.warn(
    "caqtus.utils.roi is deprecated, use caqtus.types.image instead.",
    DeprecationWarning,
)


__all__ = [
    "ArbitraryROI",
    "RectangularROI",
    "RotatedRectangularROI",
    "ROI",
    "Width",
    "Height",
]

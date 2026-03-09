"""Defines region of interest to select a subset of an image."""

from caqtus.utils import serialization
from ._arbitrary_roi import ArbitraryROI
from ._converter import converter
from ._rectangular_roi import RectangularROI
from ._roi import ROI, Width, Height
from ._rotated_rectangular_roi import RotatedRectangularROI

# TODO: Remove this once nothing relies on the serialization module
serialization.include_subclasses(ROI)


__all__ = [
    "ROI",
    "RectangularROI",
    "RotatedRectangularROI",
    "ArbitraryROI",
    "Width",
    "Height",
    "converter",
]

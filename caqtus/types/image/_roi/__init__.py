from caqtus.utils import serialization
from .arbitrary_roi import ArbitraryROI
from .converter import converter
from .rectangular_roi import RectangularROI
from .roi import ROI, Width, Height
from .rotated_rectangular_roi import RotatedRectangularROI

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

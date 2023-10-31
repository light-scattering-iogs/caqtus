from util import serialization
from .arbitrary_roi import ArbitraryROI
from .rectangular_roi import RectangularROI
from .roi import ROI

serialization.include_subclasses(
    ROI, union_strategy=serialization.include_type(tag_name="roi_type")
)

__all__ = ["ArbitraryROI", "RectangularROI", "ROI"]

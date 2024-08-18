import cattrs.strategies

from .arbitrary_roi import ArbitraryROI
from .rectangular_roi import RectangularROI
from .roi import ROI
from .rotated_rectangular_roi import RotatedRectangularROI

converter = cattrs.Converter(
    unstruct_collection_overrides={tuple: tuple},
)
"""A converter that can (un)structure ROI objects.

.. Warning::
    Only subclasses of ROI that are defined in this module have their types correctly
    unstructured.
"""

cattrs.strategies.include_subclasses(
    ROI, converter, (RectangularROI, ArbitraryROI, RotatedRectangularROI)
)

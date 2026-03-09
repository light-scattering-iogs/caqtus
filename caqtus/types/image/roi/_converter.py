import cattrs.strategies

from ._arbitrary_roi import ArbitraryROI
from ._rectangular_roi import RectangularROI
from ._roi import ROI
from ._rotated_rectangular_roi import RotatedRectangularROI

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

import pytest

from caqtus.types.image import Width, Height
from caqtus.types.image.roi import RectangularROI, ROI, ArbitraryROI, converter


@pytest.mark.parametrize(
    "roi",
    [
        RectangularROI((Width(100), Height(100)), 50, 20, 10, 5),
        ArbitraryROI((Width(100), Height(100)), ((50, 20), (10, 5), (30, 40))),
    ],
)
def test_roi_serialization(roi):
    unstructured = converter.unstructure(roi, ROI)
    structured = converter.structure(unstructured, ROI)
    assert roi == structured

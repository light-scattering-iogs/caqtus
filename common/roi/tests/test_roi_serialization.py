from roi import ROI, RectangularROI
from settings_model import YAMLSerializable
from util import serialization


def test_roi_serialization():
    roi = RectangularROI(original_image_size=(10, 20), x=1, y=2, width=3, height=4)
    assert YAMLSerializable.load(YAMLSerializable.dump(roi)) == roi
    assert serialization.structure(serialization.unstructure(roi), ROI) == roi

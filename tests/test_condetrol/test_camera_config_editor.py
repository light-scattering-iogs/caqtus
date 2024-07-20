from caqtus.gui.condetrol.device_configuration_editors.camera_configuration_editor import (
    RectangularROIEditor,
)
from caqtus.utils.roi import RectangularROI


def test_1(qtbot):
    roi = RectangularROI((100, 100), 0, 100, 0, 100)
    editor = RectangularROIEditor()
    editor.set_roi(roi)
    editor.show()
    qtbot.addWidget(editor)

    editor._x_spinbox.setValue(1)

    new_roi = editor.get_roi()

    assert new_roi == roi

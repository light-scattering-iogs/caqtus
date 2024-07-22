import copy
from typing import Optional

from PySide6.QtWidgets import QWidget, QSpinBox, QFormLayout

from caqtus.device.camera import CameraConfiguration
from caqtus.utils.roi import RectangularROI, Width, Height
from ..device_configuration_editor import FormDeviceConfigurationEditor


class CameraConfigurationEditor[T: CameraConfiguration](
    FormDeviceConfigurationEditor[T]
):
    """A widget that allows to edit the configuration of a camera.

    This widget has the same fields as the base form editor and adds a field to edit
    the region of interest of the image to take.
    """

    def __init__(self, configuration: T, parent: Optional[QWidget] = None) -> None:
        super().__init__(configuration, parent)

        self._roi_editor = RectangularROIEditor(parent=self)
        self.append_row("ROI", self._roi_editor)
        self._roi_editor.set_roi(configuration.roi)

    def get_configuration(self) -> T:
        configuration = super().get_configuration()
        configuration.roi = copy.deepcopy(self._roi_editor.get_roi())
        return configuration


class RectangularROIEditor(QWidget):
    """A widget that allows to edit a rectangular region of interest."""

    def __init__(
        self,
        max_width: int = 100,
        max_height: int = 100,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._max_width = max_width
        self._max_height = max_height

        layout = QFormLayout(self)
        layout.setContentsMargins(0, 3, 0, 0)
        self.setLayout(layout)

        self._x_spinbox = QSpinBox(self)
        layout.addRow("X", self._x_spinbox)
        self._x_spinbox.setRange(0, 0)
        self._x_spinbox.setValue(0)

        self._width_spinbox = QSpinBox(self)
        layout.addRow("Width", self._width_spinbox)
        self._width_spinbox.setRange(1, self._max_width)
        self._width_spinbox.setValue(self._max_width)

        self._y_spinbox = QSpinBox(self)
        layout.addRow("Y", self._y_spinbox)
        self._y_spinbox.setRange(0, 0)
        self._y_spinbox.setValue(0)

        self._height_spinbox = QSpinBox(self)
        layout.addRow("Height", self._height_spinbox)
        self._height_spinbox.setRange(1, self._max_height)
        self._height_spinbox.setValue(self._max_height)

        self._x_spinbox.valueChanged.connect(self._on_x_value_changed)
        self._y_spinbox.valueChanged.connect(self._on_y_value_changed)

        self._width_spinbox.valueChanged.connect(self._on_width_value_changed)
        self._height_spinbox.valueChanged.connect(self._on_height_value_changed)

    def set_roi(self, roi: RectangularROI) -> None:
        """Set the values to be displayed in the editor."""

        self._max_width = roi.original_width
        self._max_height = roi.original_height

        # We first set x and y coordinates to 0 to have the full allowed range for
        # width and height spinboxes, otherwise the range would be limited by the
        # current x and y values.

        self._x_spinbox.setValue(0)
        self._width_spinbox.setValue(roi.width)
        self._x_spinbox.setValue(roi.x)

        self._y_spinbox.setValue(0)
        self._height_spinbox.setValue(roi.height)
        self._y_spinbox.setValue(roi.y)

    def get_roi(self) -> RectangularROI:
        """Return the values of the ROI currently displayed in the editor."""

        return RectangularROI(
            x=self._x_spinbox.value(),
            y=self._y_spinbox.value(),
            width=self._width_spinbox.value(),
            height=self._height_spinbox.value(),
            original_image_size=(Width(self._max_width), Height(self._max_height)),
        )

    def _on_x_value_changed(self, x: int) -> None:
        self._width_spinbox.setRange(1, self._max_width - x)

    def _on_y_value_changed(self, y: int) -> None:
        self._height_spinbox.setRange(1, self._max_height - y)

    def _on_width_value_changed(self, width: int) -> None:
        self._x_spinbox.setRange(0, self._max_width - width)

    def _on_height_value_changed(self, height: int) -> None:
        self._y_spinbox.setRange(0, self._max_height - height)

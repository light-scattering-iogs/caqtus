import abc
import copy
from typing import TypeVar, Optional

from PySide6.QtWidgets import QWidget, QSpinBox, QFormLayout

from caqtus.device.camera import CameraConfiguration
from caqtus.utils.roi import RectangularROI, Width, Height
from ..device_configuration_editor import FormDeviceConfigurationEditor

T = TypeVar("T", bound=CameraConfiguration)


class CameraConfigurationEditor(FormDeviceConfigurationEditor[T]):
    """A widget that allows to edit the configuration of a camera."""

    @abc.abstractmethod
    def __init__(self, configuration: T, parent: Optional[QWidget] = None) -> None:
        super().__init__(configuration, parent)
        self._update_camera_fields(self.device_config)

    def get_configuration(self) -> T:
        self.device_config = self.update_config_from_ui(self.device_config)
        return self.device_config

    def set_configuration(self, device_configuration: T) -> None:
        self.device_config = device_configuration
        self.update_ui_from_config(self.device_config)

    def _update_camera_fields(self, device_config: T) -> None:
        self._left_spinbox.setRange(0, device_config.roi.original_width - 1)
        self._left_spinbox.setValue(device_config.roi.left)

        self._right_spinbox.setRange(0, device_config.roi.original_width - 1)
        self._right_spinbox.setValue(device_config.roi.right)

        self._bottom_spinbox.setRange(0, device_config.roi.original_height - 1)
        self._bottom_spinbox.setValue(device_config.roi.bottom)

        self._top_spinbox.setRange(0, device_config.roi.original_height - 1)
        self._top_spinbox.setValue(device_config.roi.top)

    @abc.abstractmethod
    def update_ui_from_config(self, device_config: T) -> None:
        self._update_camera_fields(device_config)

    @abc.abstractmethod
    def update_config_from_ui(self, device_config: T) -> T:
        device_config = copy.deepcopy(device_config)
        device_config.roi.x = self._left_spinbox.value()
        device_config.roi.width = (
            self._right_spinbox.value() - self._left_spinbox.value() + 1
        )
        device_config.roi.y = self._bottom_spinbox.value()
        device_config.roi.height = (
            self._top_spinbox.value() - self._bottom_spinbox.value() + 1
        )
        return device_config


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

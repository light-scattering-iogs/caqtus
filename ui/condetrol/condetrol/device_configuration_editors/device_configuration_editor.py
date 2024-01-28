import abc
import copy
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from core.device import DeviceConfigurationAttrs
from qabc import QABC
import black


class DeviceConfigurationEditor[T: DeviceConfigurationAttrs](QWidget, QABC):
    @abc.abstractmethod
    def set_configuration(self, device_configuration: T) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_configuration(self) -> T:
        raise NotImplementedError


class DefaultDeviceConfigurationEditor[T: DeviceConfigurationAttrs](
    DeviceConfigurationEditor[T]
):
    """Default device configuration editor.

    This editor is used when no editor is registered for a given device configuration.
    It does not allow to view or edit the device configuration.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.device_configuration: Optional[T] = None
        layout = QVBoxLayout()
        self.message_label = QLabel("No configuration selected")
        self.message_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(self.message_label)
        self.setLayout(layout)

    def set_configuration(self, device_configuration: T) -> None:
        self.device_configuration = copy.deepcopy(device_configuration)
        try:
            config = black.format_str(
                repr(self.device_configuration), mode=black.FileMode()
            )
        except black.InvalidInput:
            config = repr(self.device_configuration)
        self.message_label.setText(
            f"No custom editor is registered to edit a device configuration of type "
            f"<{type(device_configuration).__qualname__}>.\n"
            f"Consider registering an editor for this type of device configuration "
            f"when instantiating the main window.\n\n"
            f"Here is a naive representation of the device configuration:\n\n{config}"
        )

    def get_configuration(self) -> T:
        return copy.deepcopy(self.device_configuration)

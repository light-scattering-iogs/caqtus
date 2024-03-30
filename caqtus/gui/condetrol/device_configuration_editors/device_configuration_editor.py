import abc
from typing import Optional, Generic, TypeVar

from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit

import caqtus.gui.qtutil.qabc as qabc
from caqtus.device import DeviceConfigurationAttrs
from caqtus.device.configuration import DeviceServerName

T = TypeVar("T", bound=DeviceConfigurationAttrs)


class DeviceConfigurationEditor(QWidget, Generic[T], metaclass=qabc.QABCMeta):
    """Base class for device configuration editors."""

    @abc.abstractmethod
    def get_configuration(self) -> T:
        """Return the configuration displayed in the editor."""

        raise NotImplementedError


class DefaultDeviceConfigurationEditor(DeviceConfigurationEditor[T], Generic[T]):
    """Default device configuration editor.

    This editor is used when no editor is registered for a given device configuration.
    It only allows editing the remote server name.
    """

    def __init__(self, device_configuration: T, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QFormLayout()
        self.device_configuration = device_configuration
        self.remote_server_line_edit = QLineEdit(self)
        self.remote_server_line_edit.setPlaceholderText("None")
        self.remote_server_line_edit.setText(device_configuration.remote_server)
        layout.addRow("Remote server", self.remote_server_line_edit)
        self.setLayout(layout)

    def get_configuration(self) -> T:
        text = self.remote_server_line_edit.text()
        if text == "":
            self.device_configuration.remote_server = None
        else:
            self.device_configuration.remote_server = DeviceServerName(text)
        return self.device_configuration

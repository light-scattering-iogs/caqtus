import abc
from typing import Optional, Generic, TypeVar

from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit

import caqtus.gui.qtutil.qabc as qabc
from caqtus.device import DeviceConfiguration
from caqtus.device.configuration import DeviceServerName

T = TypeVar("T", bound=DeviceConfiguration)


class DeviceConfigurationEditor(QWidget, Generic[T], metaclass=qabc.QABCMeta):
    """A widget that allows to edit the configuration of a device.

    This class is generic in the type of the device configuration it presents.
    """

    @abc.abstractmethod
    def get_configuration(self) -> T:
        """Return the configuration currently displayed in the editor."""

        raise NotImplementedError


class FormDeviceConfigurationEditor(DeviceConfigurationEditor[T], Generic[T]):
    """An editor for a device configuration displaying a list of fields.

    Attributes:
        device_configuration: The device configuration stored in the editor.
        form: The form layout used to display the different fields of the configuration.
        remote_server_line_edit: The line edit used to edit the remote server name.
        It is placed at index 0 in the form layout.
    """

    def __init__(self, device_configuration: T, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.form = QFormLayout()
        self.device_configuration = device_configuration
        self.remote_server_line_edit = QLineEdit(self)
        self.remote_server_line_edit.setPlaceholderText("None")
        self.remote_server_line_edit.setText(device_configuration.remote_server)
        self.form.addRow("Remote server", self.remote_server_line_edit)
        self.setLayout(self.form)

    def get_configuration(self) -> T:
        text = self.remote_server_line_edit.text()
        if text == "":
            self.device_configuration.remote_server = None
        else:
            self.device_configuration.remote_server = DeviceServerName(text)
        return self.device_configuration

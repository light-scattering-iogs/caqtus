import abc
import copy
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
    """Displays a list of fields to edit the configuration of a device.

    Widgets of this class initially only present a single field to edit the remote
    server name.

    Other device specific fields can be added by calling the :meth:`insert_row` method.
    """

    def __init__(self, device_configuration: T, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.form = QFormLayout()
        self.device_configuration = copy.deepcopy(device_configuration)
        self.remote_server_line_edit = QLineEdit(self)
        self.remote_server_line_edit.setPlaceholderText("None")
        self.set_remote_server(self.device_configuration.remote_server)
        self.form.addRow("Remote server", self.remote_server_line_edit)
        self.setLayout(self.form)

    def append_row(self, label: str, widget: QWidget):
        """Append a widget field at the end of the form."""

        self.form.addRow(label, widget)

    def insert_row(self, label: str, widget: QWidget, row: int):
        """Insert a widget field at the specified row."""

        self.form.insertRow(row, label, widget)

    def get_configuration(self) -> T:
        """Return the initial configuration with fields updated from the UI.

        Returns:
            The configuration that was passed to the constructor with the remote server
            field updated to the value set in the UI.

            Subclasses should override this method to update other fields as well.
        """

        configuration = copy.deepcopy(self.device_configuration)
        configuration.remote_server = self.read_remote_server()
        return configuration

    def set_remote_server(self, remote_server: Optional[DeviceServerName]) -> None:
        """Set the remote server name in the editor."""

        self.remote_server_line_edit.setText(remote_server or "")

    def read_remote_server(self) -> Optional[DeviceServerName]:
        """Read the remote server name from the editor."""

        text = self.remote_server_line_edit.text()
        if text == "":
            return None
        return DeviceServerName(text)

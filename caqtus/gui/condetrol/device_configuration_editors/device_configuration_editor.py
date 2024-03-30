import abc
import copy
from typing import Optional, Generic, TypeVar

import caqtus.gui.qtutil.qabc as qabc
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit
from caqtus.device import DeviceConfigurationAttrs

T = TypeVar("T", bound=DeviceConfigurationAttrs)


class DeviceConfigurationEditor(QWidget, Generic[T], metaclass=qabc.QABCMeta):
    @abc.abstractmethod
    def set_configuration(self, device_configuration: T) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_configuration(self) -> T:
        raise NotImplementedError


class DefaultDeviceConfigurationEditor(DeviceConfigurationEditor[T], Generic[T]):
    """Default device configuration editor.

    This editor is used when no editor is registered for a given device configuration.
    It only allows editing the remote server name.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.device_configuration: Optional[T] = None
        layout = QFormLayout()
        self.remote_server_line_edit = QLineEdit(self)
        self.remote_server_line_edit.setPlaceholderText("Name")
        layout.addRow("Remote server", self.remote_server_line_edit)
        self.setLayout(layout)

    def set_configuration(self, device_configuration: T) -> None:
        self.device_configuration = copy.deepcopy(device_configuration)
        self.remote_server_line_edit.setText(device_configuration.remote_server)

    def get_configuration(self) -> T:
        config = copy.deepcopy(self.device_configuration)
        config.remote_server = self.remote_server_line_edit.text()
        return config

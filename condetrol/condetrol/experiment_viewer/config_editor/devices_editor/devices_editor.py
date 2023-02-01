import copy
from typing import Optional

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from device_config import DeviceConfiguration
from experiment_config import ExperimentConfig, SiglentSDG6000XConfiguration
from .devices_editor_editor_ui import Ui_DevicesEditor
from ..config_settings_editor import ConfigSettingsEditor

DEVICE_TYPES = ["SiglentSDG6000XWaveformGenerator"]


class DevicesEditor(ConfigSettingsEditor, Ui_DevicesEditor):
    device_added = pyqtSignal(DeviceConfiguration)
    def __init__(
        self, config: ExperimentConfig, label: str, parent: Optional[QWidget] = None
    ):
        super().__init__(config, label, parent)
        self.config = config
        self.setupUi(self)

        for device_type in DEVICE_TYPES:
            self.device_type_combobox.addItem(device_type)

        for remote_server in self.config.device_servers:
            self.remote_server_combobox.addItem(remote_server)

        self.add_button.clicked.connect(self.add_device_config)

    def add_device_config(self):
        device_type = self.device_type_combobox.currentText()
        device_name = self.device_name_lineedit.text()
        device_server = self.remote_server_combobox.currentText()
        new_config = self.create_default_device_config(
            device_type, device_name, device_server
        )
        self.config.add_device_config(new_config)
        # noinspection PyUnresolvedReferences
        self.device_added.emit(copy.deepcopy(new_config))

    def create_default_device_config(
        self, device_type: str, device_name: str, remote_server: str
    ) -> DeviceConfiguration:
        if device_type == "SiglentSDG6000XWaveformGenerator":
            return SiglentSDG6000XConfiguration(
                device_name=device_name, remote_server=remote_server
            )

        raise ValueError(
            f"Could not create a new configuration for device type <{device_type}>"
        )

    def get_experiment_config(self) -> ExperimentConfig:
        return self.config

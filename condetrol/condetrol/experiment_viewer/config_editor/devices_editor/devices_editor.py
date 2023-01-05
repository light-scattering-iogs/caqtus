from typing import Optional

from PyQt5.QtWidgets import QWidget

from experiment_config import ExperimentConfig
from ..config_settings_editor import ConfigSettingsEditor
from .devices_editor_editor_ui import Ui_DevicesEditor


class DevicesEditor(ConfigSettingsEditor, Ui_DevicesEditor):
    def __init__(
        self, config: ExperimentConfig, label: str, parent: Optional[QWidget] = None
    ):
        super().__init__(config, label, parent)
        self.config = config
        self.setupUi(self)


    def add_device(self):
        device = DeviceConfig()
        self.devices.append(device)
        self.device_list.addItem(device.name)
        self.device_list.setCurrentRow(self.device_list.count() - 1)

    def remove_device(self):
        if self.device_list.count():
            self.devices.pop(self.device_list.currentRow())
            self.device_list.takeItem(self.device_list.currentRow())

    def get_experiment_config(self) -> ExperimentConfig:
        return self.config

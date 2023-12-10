import copy
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from device.configuration import DeviceConfigurationAttrs
from device.name import DeviceName
from device_server.name import DeviceServerName
from experiment.configuration import (
    ExperimentConfig,
    ElliptecELL14RotationStageConfiguration,
    SwabianPulseStreamerConfiguration,
)
from .devices_editor_editor_ui import Ui_DevicesEditor
from ..config_settings_editor import ConfigSettingsEditor

DEVICE_TYPES = ["ElliptecELL14RotationStage", "SwabianPulseStreamer"]


class DevicesEditor(ConfigSettingsEditor, Ui_DevicesEditor):
    device_added = pyqtSignal(DeviceConfigurationAttrs)

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, label, parent)
        self.setupUi(self)

        for device_type in DEVICE_TYPES:
            self.device_type_combobox.addItem(device_type)

        for remote_server in self._experiment_config.device_servers:
            self.remote_server_combobox.addItem(remote_server)

        self.add_button.clicked.connect(self.add_device_config)

    def add_device_config(self):
        device_type = self.device_type_combobox.currentText()
        device_name = DeviceName(self.device_name_lineedit.text())
        device_server = DeviceServerName(self.remote_server_combobox.currentText())
        new_config = self.create_default_device_config(device_type, device_server)
        self._experiment_config.add_device_config(device_name, new_config)
        # noinspection PyUnresolvedReferences
        self.device_added.emit(copy.deepcopy(new_config))

    @staticmethod
    def create_default_device_config(
        device_type: str, remote_server: DeviceServerName
    ) -> DeviceConfigurationAttrs:
        if device_type == "ElliptecELL14RotationStage":
            config = ElliptecELL14RotationStageConfiguration.get_default_config(
                remote_server
            )
            return config
        elif device_type == "SwabianPulseStreamer":
            config = SwabianPulseStreamerConfiguration.get_default_config(remote_server)
            return config

        raise ValueError(
            f"Could not create a new configuration for device type <{device_type}>"
        )

    def get_experiment_config(self) -> ExperimentConfig:
        return super().get_experiment_config()

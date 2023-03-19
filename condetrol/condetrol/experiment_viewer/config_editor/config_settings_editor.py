from abc import abstractmethod
from typing import Optional

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

from device_config import DeviceConfiguration
from experiment.configuration import ExperimentConfig
from qabc import QABC
from yaml_clipboard_mixin import YAMLClipboardMixin


class ConfigSettingsEditor(QWidget, QABC):
    """An abstract interface defining how a widget should edit a group of settings

    Every time a settings group is selected in the config editor, a widget is created to edit that group.
    """

    def __init__(
        self,
        config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

    @abstractmethod
    def get_experiment_config(self) -> ExperimentConfig:
        ...

    @staticmethod
    def strip_device_prefix(tree_label: str) -> str:
        """

        example: strip_device_prefix("Devices\dev A") == "dev A"
        """

        prefix = tree_label[0:8]
        if prefix != "Devices\\":
            raise ValueError(
                f"Invalid prefix for device tree label: {tree_label} should start with"
                " 'Devices\\'"
            )
        return tree_label[8:]


class NotImplementedDeviceConfigEditor(ConfigSettingsEditor, YAMLClipboardMixin):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(config=experiment_config, tree_label=tree_label, parent=parent)

        self.config = experiment_config
        self.device_name = self.strip_device_prefix(tree_label)
        device_config = self.config.get_device_config(self.device_name)
        device_type = device_config.get_device_type()
        layout = QHBoxLayout()
        layout.addWidget(
            QLabel(
                f"There is no widget implemented for a device of type <{device_type}>"
            )
        )
        self.setLayout(layout)

    def convert_to_external_use(self):
        return self.config.get_device_config(self.device_name)

    def update_from_external_source(self, new_config: DeviceConfiguration):
        if new_config.device_name != self.device_name:
            raise ValueError(
                f"Cannot change device name from {self.device_name} to {new_config.device_name}"
            )
        old_config = self.config.get_device_config(self.device_name)
        if not isinstance(new_config, type(old_config)):
            raise TypeError(f"Expected {type(old_config)} got {type(new_config)}")
        self.config.set_device_config(self.device_name, new_config)

    def get_experiment_config(self) -> ExperimentConfig:
        return self.config

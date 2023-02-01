from typing import Optional

from PyQt5.QtWidgets import QWidget

from experiment_config import ExperimentConfig
from .editor_widget_ui import Ui_EditorWidget
from ..config_settings_editor import ConfigSettingsEditor


class SiglentSDG6000XConfigEditor(ConfigSettingsEditor, Ui_EditorWidget):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)
        self.setupUi(self)

        self.config = experiment_config
        self.device_name = self.strip_device_prefix(tree_label)
        # self.siglent_config = self.config.get_device_config(self.device_name)

    def get_experiment_config(self) -> ExperimentConfig:
        self.config.set_device_config(self.device_name, self.siglent_config)
        return self.config

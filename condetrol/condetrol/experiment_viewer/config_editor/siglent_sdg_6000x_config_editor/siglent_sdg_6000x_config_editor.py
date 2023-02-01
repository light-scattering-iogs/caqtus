from typing import Optional

from PyQt5.QtWidgets import QWidget, QVBoxLayout

from experiment_config import ExperimentConfig
from .editor_widget_ui import Ui_EditorWidget
from ..config_settings_editor import ConfigSettingsEditor
from .sine_editor_ui import Ui_SineEditor


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
        self.siglent_config = self.config.get_device_config(self.device_name)

        layout_1 = QVBoxLayout()
        layout_1.addWidget(SineEditor())
        self.tab_1.setLayout(layout_1)

        self.setup_server_combobox()

    def setup_server_combobox(self):
        for remote_server in self.config.device_servers:
            self.remote_server_combobox.addItem(remote_server)
        self.remote_server_combobox.setCurrentText(self.siglent_config.remote_server)

    def get_experiment_config(self) -> ExperimentConfig:
        self.read_server_combobox()
        self.config.set_device_config(self.device_name, self.siglent_config)
        return self.config

    def read_server_combobox(self):
        self.siglent_config.remote_server = self.remote_server_combobox.currentText()

class SineEditor(QWidget, Ui_SineEditor):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

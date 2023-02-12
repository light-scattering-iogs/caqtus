from typing import Optional

from PyQt6.QtWidgets import QFormLayout, QWidget, QLineEdit

from condetrol.widgets import SaveFileWidget
from experiment_config import ExperimentConfig, get_config_path
from ..config_settings_editor import ConfigSettingsEditor


class SystemSettingsEditor(ConfigSettingsEditor):
    """A widget that allow to edit the system settings

    This includes the path to store the config file and the database path to store the
    experiment data.
    """

    def get_experiment_config(self) -> ExperimentConfig:
        self.config.database_url = self.database_url_widget.text()
        return self.config

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.config = experiment_config

        self.config_path_widget = SaveFileWidget(
            get_config_path(), "Edit config path...", "config (*.yaml)"
        )
        self.layout.insertRow(0, "Config path", self.config_path_widget)
        self.config_path_widget.setEnabled(False)

        self.database_url_widget = QLineEdit(str(self.config.database_url))
        self.layout.insertRow(1, "Database url", self.database_url_widget)

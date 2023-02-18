from typing import Optional

from PyQt6.QtWidgets import QFormLayout, QWidget

from experiment.configuration import ExperimentConfig
from ..config_settings_editor import ConfigSettingsEditor


class SystemSettingsEditor(ConfigSettingsEditor):
    """A widget that allow to edit the system settings

    This includes the path to store the config file and the database path to store the
    experiment data.
    """

    def get_experiment_config(self) -> ExperimentConfig:
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

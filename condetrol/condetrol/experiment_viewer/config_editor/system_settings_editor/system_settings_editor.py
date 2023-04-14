from copy import deepcopy
from typing import Optional

from PyQt6.QtWidgets import QFormLayout, QWidget

from experiment.configuration import ExperimentConfig
from .system_settings_editor_ui import Ui_SystemSettingsEditor
from ..config_settings_editor import ConfigSettingsEditor


class SystemSettingsEditor(ConfigSettingsEditor, Ui_SystemSettingsEditor):
    """A widget that allow to edit the system settings.

    Only the mock experiment checkbox is currently shown.
    """

    def get_experiment_config(self) -> ExperimentConfig:
        self.config = self.update_config(self.config)
        return deepcopy(self.config)

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        self.config = deepcopy(experiment_config)
        self.setupUi(self)
        self.update_ui(self.config)

    def update_ui(self, experiment_config: ExperimentConfig):
        """Update the UI to match the experiment config."""

        self._mock_experiment_checkbox.setChecked(experiment_config.mock_experiment)

    def update_config(self, config: ExperimentConfig) -> ExperimentConfig:
        """Update the experiment config to match the UI."""

        config = deepcopy(config)
        config.mock_experiment = self._mock_experiment_checkbox.isChecked()
        return config

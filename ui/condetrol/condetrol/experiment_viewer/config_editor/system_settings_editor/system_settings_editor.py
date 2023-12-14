import copy
from typing import Optional

from PyQt6.QtWidgets import QWidget

from core.session import ExperimentConfig
from .system_settings_editor_ui import Ui_SystemSettingsEditor
from ..config_settings_editor import ConfigSettingsEditor


class SystemSettingsEditor(ConfigSettingsEditor, Ui_SystemSettingsEditor):
    """A widget that allow to edit the system settings.

    Only the mock experiment checkbox is currently shown.
    """

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        self.setupUi(self)
        self.update_ui(self._experiment_config)

    def update_ui(self, experiment_config: ExperimentConfig):
        """Update the UI to match the experiment config."""

        self._mock_experiment_checkbox.setChecked(experiment_config.mock_experiment)

    def update_config(self, config: ExperimentConfig) -> ExperimentConfig:
        """Update the experiment config to match the UI."""

        config = copy.deepcopy(config)
        config.mock_experiment = self._mock_experiment_checkbox.isChecked()
        return config

    def get_experiment_config(self) -> ExperimentConfig:
        """Return a copy of the experiment config currently shown in the UI."""

        self._experiment_config = self.update_config(self._experiment_config)
        return super().get_experiment_config()

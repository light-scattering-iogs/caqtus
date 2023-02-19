import logging
from typing import Optional

from PyQt6.QtWidgets import QWidget

from experiment.configuration import ExperimentConfig
from spincore_sequencer.configuration import SpincoreSequencerConfiguration
from .spincore_editor_ui import Ui_SpincoreEditor
from ..config_settings_editor import ConfigSettingsEditor

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

ns = 1e-9


class SpincoreConfigEditor(ConfigSettingsEditor, Ui_SpincoreEditor):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        self.device_name = self.strip_device_prefix(tree_label)
        self.experiment_config = experiment_config
        self.config: SpincoreSequencerConfiguration = (
            experiment_config.get_device_config(self.device_name)
        )

        self.setupUi(self)
        self.setup_ui_from_config(self.config)

    def get_experiment_config(self) -> ExperimentConfig:
        self.write_ui_to_config(self.config)
        self.experiment_config.set_device_config(self.device_name, self.config)
        return self.experiment_config

    def setup_ui_from_config(self, config: SpincoreSequencerConfiguration):
        self.board_number_spinbox.setValue(config.board_number)
        self.time_step_spinbox.setValue(config.time_step / ns)

    def write_ui_to_config(self, config: SpincoreSequencerConfiguration):
        config.board_number = self.board_number_spinbox.value()
        config.time_step = self.time_step_spinbox.value() * ns
        return config

from typing import Optional

from PyQt6.QtWidgets import QWidget

from experiment.configuration import ExperimentConfig, OrcaQuestCameraConfiguration
from .orca_quest_config_editor_ui import Ui_OrcaQuestConfigEditor
from ..config_settings_editor import DeviceConfigEditor


class OrcaQuestConfigEditor(DeviceConfigEditor, Ui_OrcaQuestConfigEditor):
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
        orca_quest_config: OrcaQuestCameraConfiguration = (
            experiment_config.get_device_config(self.device_name)
        )

        self._remote_server_combobox.set_servers(
            experiment_config.get_device_server_names()
        )
        self._remote_server_combobox.set_current_server(orca_quest_config.remote_server)
        self._camera_number_spinbox.setValue(orca_quest_config.camera_number)
        self._left_spinbox.setRange(0, orca_quest_config.roi.original_width - 1)
        self._left_spinbox.setValue(orca_quest_config.roi.left)

        self._right_spinbox.setRange(0, orca_quest_config.roi.original_width - 1)
        self._right_spinbox.setValue(orca_quest_config.roi.right)

        self._bottom_spinbox.setRange(0, orca_quest_config.roi.original_height - 1)
        self._bottom_spinbox.setValue(orca_quest_config.roi.bottom)

        self._top_spinbox.setRange(0, orca_quest_config.roi.original_height - 1)
        self._top_spinbox.setValue(orca_quest_config.roi.top)

    def get_experiment_config(self) -> ExperimentConfig:
        self._experiment_config = self.update_config(self._experiment_config)
        return super().get_experiment_config()

    def update_config(self, experiment_config: ExperimentConfig) -> ExperimentConfig:
        experiment_config = experiment_config.copy(deep=True)
        config: OrcaQuestCameraConfiguration = experiment_config.get_device_config(
            self.device_name
        )
        config.remote_server = self._remote_server_combobox.get_current_server()
        config.camera_number = self._camera_number_spinbox.value()
        config.roi.x = self._left_spinbox.value()
        config.roi.width = self._right_spinbox.value() - self._left_spinbox.value() + 1
        config.roi.y = self._top_spinbox.value()
        config.roi.height = self._top_spinbox.value() - self._bottom_spinbox.value() + 1
        experiment_config.set_device_config(self.device_name, config)
        return experiment_config

    def update_from_external_source(self, new_config: OrcaQuestCameraConfiguration):
        super().update_from_external_source(new_config)
        self.update_ui(self._experiment_config)

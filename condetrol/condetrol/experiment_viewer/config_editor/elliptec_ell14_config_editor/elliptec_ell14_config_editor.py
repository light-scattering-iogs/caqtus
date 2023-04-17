from typing import Optional

from PyQt6.QtWidgets import QWidget

from experiment.configuration import (
    ExperimentConfig,
    ElliptecELL14RotationStageConfiguration,
)
from .elliptec_ell14_config_editor_ui import Ui_ElliptecELL14RotationStageConfigEditor
from ..config_settings_editor import DeviceConfigEditor


class ElliptecELL14RotationStageConfigEditor(
    DeviceConfigEditor, Ui_ElliptecELL14RotationStageConfigEditor
):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)
        self.setupUi(self)

        self.update_ui(self._experiment_config)

    def get_experiment_config(self) -> ExperimentConfig:
        new_config = self._experiment_config.get_device_config(self.device_name)
        self.write_ui_to_config(new_config)
        self._experiment_config.set_device_config(self.device_name, new_config)
        return super().get_experiment_config()

    def update_ui(self, experiment_config: ExperimentConfig):
        config: ElliptecELL14RotationStageConfiguration = (
            experiment_config.get_device_config(self.device_name)
        )
        self._remote_server_combobox.set_servers(
            experiment_config.get_device_server_names()
        )
        self._remote_server_combobox.set_current_server(config.remote_server)
        self._serial_port_widget.set_port(config.serial_port)
        self._device_id_spinbox.setValue(config.device_id)
        self._angle_line_edit.set_expression(config.position)

    def write_ui_to_config(self, config: ElliptecELL14RotationStageConfiguration):
        config.remote_server = self._remote_server_combobox.get_current_server()
        config.serial_port = self._serial_port_widget.get_port()
        config.device_id = self._device_id_spinbox.value()
        config.position = self._angle_line_edit.get_expression()

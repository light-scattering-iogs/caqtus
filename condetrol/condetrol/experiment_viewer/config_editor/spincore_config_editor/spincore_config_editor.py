import logging
from typing import Optional

from PyQt6.QtWidgets import QWidget

from experiment.configuration import ExperimentConfig
from spincore_sequencer.configuration import SpincoreSequencerConfiguration
from .spincore_editor_ui import Ui_SpincoreEditor
from ..channel_model import ChannelsModel
from ..color_delegate import ColorCellDelegate
from ..config_settings_editor import DeviceConfigEditor

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

ns = 1e-9


class SpincoreConfigEditor(DeviceConfigEditor, Ui_SpincoreEditor):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        config: SpincoreSequencerConfiguration = (
            self._experiment_config.get_device_config(self.device_name)
        )

        self.setupUi(self)
        self.setup_ui_from_config(config)
        self.channels_table_view.setItemDelegateForColumn(1, ColorCellDelegate())

    def get_experiment_config(self) -> ExperimentConfig:
        new_config = self._experiment_config.get_device_config(self.device_name)
        self.write_ui_to_config(new_config)
        self._experiment_config.set_device_config(self.device_name, new_config)
        return super().get_experiment_config()

    def setup_ui_from_config(self, config: SpincoreSequencerConfiguration):
        self.board_number_spinbox.setValue(config.board_number)
        self.time_step_spinbox.setValue(config.time_step / ns)
        self.channels_table_view.setModel(SpincoreChannelsModel(config))
        self.channels_table_view.resizeColumnToContents(0)

    def write_ui_to_config(self, config: SpincoreSequencerConfiguration):
        config.board_number = self.board_number_spinbox.value()
        config.time_step = self.time_step_spinbox.value() * ns
        return config

    def update_from_external_source(self, new_config: SpincoreSequencerConfiguration):
        super().update_from_external_source(new_config)
        self.setup_ui_from_config(new_config)


class SpincoreChannelsModel(ChannelsModel):
    pass

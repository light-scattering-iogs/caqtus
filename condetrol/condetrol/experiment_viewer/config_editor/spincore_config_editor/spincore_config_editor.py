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
        self.update_ui(config)
        self.channels_table_view.setItemDelegateForColumn(1, ColorCellDelegate())

    def get_experiment_config(self) -> ExperimentConfig:
        self._experiment_config = self.update_config(self._experiment_config)
        return super().get_experiment_config()

    def update_ui(self, config: SpincoreSequencerConfiguration):
        self.board_number_spinbox.setValue(config.board_number)
        self.time_step_spinbox.setValue(config.time_step / ns)
        self.channels_table_view.setModel(SpincoreChannelsModel(config))
        self.channels_table_view.resizeColumnToContents(0)

    def update_config(self, experiment_config: ExperimentConfig) -> ExperimentConfig:
        experiment_config = experiment_config.copy(deep=True)
        config: SpincoreSequencerConfiguration = experiment_config.get_device_config(
            self.device_name
        )

        model: SpincoreChannelsModel = self.channels_table_view.model()
        table_config: SpincoreSequencerConfiguration = model.get_config()
        config.channel_descriptions = table_config.channel_descriptions
        config.channel_colors = table_config.channel_colors

        config.board_number = self.board_number_spinbox.value()
        config.time_step = self.time_step_spinbox.value() * ns
        experiment_config.set_device_config(self.device_name, config)
        return experiment_config

    def update_from_external_source(self, new_config: SpincoreSequencerConfiguration):
        super().update_from_external_source(new_config)
        self.update_ui(new_config)


class SpincoreChannelsModel(ChannelsModel):
    def __init__(self, config: SpincoreSequencerConfiguration, *args, **kwargs):
        super().__init__(config, *args, **kwargs)

    def get_config(self) -> SpincoreSequencerConfiguration:
        config = super().get_config()
        if not isinstance(config, SpincoreSequencerConfiguration):
            raise TypeError("Expected SpincoreSequencerConfiguration")
        return config

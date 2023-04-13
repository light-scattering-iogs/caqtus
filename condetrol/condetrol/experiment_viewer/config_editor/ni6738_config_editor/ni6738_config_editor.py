import logging
from typing import Optional

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtWidgets import QWidget

from device_config.channel_config import AnalogChannelConfiguration
from experiment.configuration import ExperimentConfig
from ni6738_analog_card.configuration import NI6738SequencerConfiguration
from .ni6738_editor_ui import Ui_NI6738Editor
from ..channel_model import ChannelsModel
from ..color_delegate import ColorCellDelegate
from ..config_settings_editor import DeviceConfigEditor
from ..mapping_editor import MappingDelegate

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

us = 1e-6


class NI6738ConfigEditor(DeviceConfigEditor, Ui_NI6738Editor):
    """NI 6738 analog card configuration widget

    This widget has fields for the device ID and the time step, as well as a table
    to configure the channels.
    """

    def __init__(
        self,
        experiment_config: ExperimentConfig,
        tree_label: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(experiment_config, tree_label, parent)

        config: NI6738SequencerConfiguration = (
            self._experiment_config.get_device_config(self.device_name)
        )

        self.color_delegate = ColorCellDelegate()
        self.mapping_delegate = MappingDelegate()
        self.setupUi(self)
        self.setup_ui_from_config(config)

    def get_experiment_config(self) -> ExperimentConfig:
        new_config = self._experiment_config.get_device_config(self.device_name)
        self.write_ui_to_config(new_config)
        self._experiment_config.set_device_config(self.device_name, new_config)
        return self._experiment_config

    def setup_ui_from_config(self, config: NI6738SequencerConfiguration):
        self.device_id_line_edit.setText(config.device_id)
        self.time_step_spinbox.setValue(config.time_step / us)
        self.channels_table_view.setModel(AnalogChannelsModel(config))
        self.channels_table_view.resizeColumnToContents(0)
        self.channels_table_view.setItemDelegateForColumn(1, self.color_delegate)
        self.channels_table_view.setItemDelegateForColumn(2, self.mapping_delegate)

    def write_ui_to_config(self, config: NI6738SequencerConfiguration):
        config.device_id = self.device_id_line_edit.text()

        # There is an issue here because 2.5 * 1e-6 == 2.4999999999999998e-06 which is
        # lower than the minimum limit of 2.5e-06, so we deal with this value explicitly
        if self.time_step_spinbox.value() == 2.5:
            new_value = 2.5e-6
        else:
            new_value = self.time_step_spinbox.value() * us
        config.time_step = new_value
        return config

    def update_from_external_source(self, new_config: NI6738SequencerConfiguration):
        super().update_from_external_source(new_config)
        self.setup_ui_from_config(new_config)


class AnalogChannelsModel(ChannelsModel):
    """Add a unit column to the channel model"""

    def __init__(self, config: AnalogChannelConfiguration, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self._config: AnalogChannelConfiguration = config

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return super().columnCount(parent) + 1

    def data(self, index: QModelIndex, role: int = ...):
        if index.column() == 2:
            channel = index.row()
            mapping = self._config.channel_mappings[channel]
            if role == Qt.ItemDataRole.DisplayRole:
                if mapping is not None:
                    return mapping.format_units()
                else:
                    return "NA"
            elif role == Qt.ItemDataRole.EditRole:
                return mapping
        else:
            return super().data(index, role)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal and section == 2:
                return "Unit"
            else:
                return super().headerData(section, orientation, role)

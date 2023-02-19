import logging
from copy import deepcopy
from typing import Optional

from PyQt6 import QtCore
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QPainter, QBrush, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QColorDialog,
)
from pydantic.color import Color

from device_config.channel_config import ChannelSpecialPurpose
from experiment.configuration import ExperimentConfig
from settings_model import YAMLSerializable
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
        self.channels_table_view.setItemDelegateForColumn(1, ColorCellDelegate())

    def get_experiment_config(self) -> ExperimentConfig:
        self.write_ui_to_config(self.config)
        self.experiment_config.set_device_config(self.device_name, self.config)
        return self.experiment_config

    def setup_ui_from_config(self, config: SpincoreSequencerConfiguration):
        self.board_number_spinbox.setValue(config.board_number)
        self.time_step_spinbox.setValue(config.time_step / ns)
        self.channels_table_view.setModel(ChannelsModel(config))
        self.channels_table_view.resizeColumnsToContents()

    def write_ui_to_config(self, config: SpincoreSequencerConfiguration):
        config.board_number = self.board_number_spinbox.value()
        config.time_step = self.time_step_spinbox.value() * ns
        return config


class ChannelsModel(QAbstractTableModel):
    def __init__(self, config: SpincoreSequencerConfiguration, *args, **kwargs):
        self._config = config
        super().__init__(*args, **kwargs)

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return self._config.number_channels

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 2

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                return self.get_channel_description(index.row())
            elif index.column() == 1:
                return self._config.channel_colors[index.row()]

    def get_channel_description(self, channel: int) -> Optional[str]:
        desc = self._config.channel_descriptions[channel]
        match desc:
            case str(desc):
                return desc
            case ChannelSpecialPurpose(purpose=purpose):
                if purpose == "Unused":
                    return ""
                return f"!ChannelSpecialPurpose {purpose}"

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        channel = index.row()
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                return self.set_channel_description(channel, value)
            elif index.column() == 1:
                return self.set_channel_color(channel, value)
        return False

    def set_channel_description(self, channel: int, value):
        value = YAMLSerializable.load(value)
        descriptions = deepcopy(self._config.channel_descriptions)
        change = False
        match value:
            case None:
                descriptions[channel] = ChannelSpecialPurpose.unused()
                change = True
            case str(value):
                descriptions[channel] = value
                change = True
            case ChannelSpecialPurpose():
                descriptions[channel] = value
                change = True
        self._config.channel_descriptions = descriptions  # triggers validation
        return change

    def set_channel_color(self, channel: int, value):
        colors = deepcopy(self._config.channel_colors)
        colors[channel] = value
        self._config.channel_colors = colors
        return True

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return "Description"
                elif section == 1:
                    return "Color"
            else:
                return section

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )


class ColorCellDelegate(QStyledItemDelegate):
    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        # noinspection PyTypeChecker
        model = index.model()
        color = model.data(index, Qt.ItemDataRole.DisplayRole)
        super().paint(painter, option, index)
        if isinstance(color, Color):
            color = color.as_rgb_tuple(alpha=True)
            color = color[0:3] + (int(color[3] * 255),)
            brush = QBrush(QColor.fromRgb(*color))
            painter.fillRect(option.rect, brush)
            if option.state & QStyle.StateFlag.State_Selected:
                c = option.palette.highlight().color()
                c.setAlphaF(0.8)
                brush = QBrush(c)
                painter.fillRect(option.rect, brush)

    def createEditor(
        self, parent: QWidget, option: "QStyleOptionViewItem", index: QtCore.QModelIndex
    ) -> QWidget:
        widget = QColorDialog(parent)
        widget.setOption(QColorDialog.ColorDialogOption.NoButtons, True)
        widget.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        return widget

    def setEditorData(self, editor: QColorDialog, index: QtCore.QModelIndex) -> None:
        color = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if color is not None:
            color = color.as_rgb_tuple(alpha=True)
            color = color[0:3] + (int(color[3] * 255),)
            editor.setCurrentColor(QColor.fromRgb(*color))

    def setModelData(
        self,
        editor: QColorDialog,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ) -> None:
        color = editor.currentColor().getRgb()
        color = Color(color[0:3] + (color[3] / 255,))
        model.setData(index, color, Qt.ItemDataRole.EditRole)

from copy import deepcopy
from typing import Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from device_config.channel_config import ChannelConfiguration, ChannelSpecialPurpose
from settings_model import YAMLSerializable


class ChannelsModel(QAbstractTableModel):
    """A model to display and edit the channel descriptions and colors of a device."""

    def __init__(self, config: ChannelConfiguration, *args, **kwargs):
        """Initialize the model.

        Args:
            config: The channel configuration to display and edit. The model will keep a
            reference to this object and edit it directly. No copy is made.
        """

        self._config = config
        super().__init__(*args, **kwargs)

    def get_config(self) -> ChannelConfiguration:
        return self._config.copy(deep=True)

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

from collections.abc import Sequence
from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.device.sequencer.configuration import ChannelConfiguration

delay_multiplier = 1e-6


class SequencerChannelsModel(QAbstractTableModel):
    """A model to display and edit the channels of a sequencer device."""

    def __init__(self, channels: Sequence[ChannelConfiguration], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channels = tuple(channels)

    @property
    def channels(self) -> tuple[ChannelConfiguration, ...]:
        return self._channels

    @channels.setter
    def channels(self, channels: tuple[ChannelConfiguration, ...]):
        self.beginResetModel()
        self._channels = channels
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._channels)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 5

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.FontRole and index.column() == 0:
            if self._channels[index.row()].description is None:
                font = QFont()
                font.setItalic(True)
                return font
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                description = self._channels[index.row()].description
                if description is None:
                    if role == Qt.ItemDataRole.DisplayRole:
                        return "unused"
                    else:
                        return ""
                else:
                    return description
            elif index.column() == 1:
                return self._channels[index.row()].color
            elif index.column() == 2:
                return self._channels[index.row()].default_value
            elif index.column() == 3:
                return self._channels[index.row()].output_mapping
            elif index.column() == 4:
                return self._channels[index.row()].delay / delay_multiplier

    def setData(
        self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        channel = index.row()
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                if str(value) == "":
                    self._channels[channel].description = None
                else:
                    self._channels[channel].description = str(value)
                return True
            elif index.column() == 1:
                self._channels[channel].color = value
                return True
            elif index.column() == 2:
                self._channels[channel].default_value = value
                return True
            elif index.column() == 3:
                self._channels[channel].output_mapping = value
                return True
            elif index.column() == 4:
                self._channels[channel].delay = value * delay_multiplier
                return True
        return super().setData(index, value, role)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str:
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                if section == 0:
                    return "Description"
                elif section == 1:
                    return "Color"
                elif section == 2:
                    return "Default"
                elif section == 3:
                    return "Output"
                elif section == 4:
                    return "Delay [µs]"
        elif orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(section)
        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )

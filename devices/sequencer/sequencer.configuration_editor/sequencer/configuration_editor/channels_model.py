from collections.abc import Sequence
from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex
from PyQt6.QtCore import Qt

from sequencer.configuration import ChannelConfiguration


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
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                return self._channels[index.row()].description
            elif index.column() == 1:
                return self._channels[index.row()].color
            elif index.column() == 2:
                return self._channels[index.row()].default_value
            elif index.column() == 3:
                return self._channels[index.row()].output_mapping
            elif index.column() == 4:
                return self._channels[index.row()].delay
        return super().data(index, role)

    def setData(
        self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        channel = index.row()
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == 0:
                self._channels[channel].description = value
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
                self._channels[channel].delay = value
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
                    return "Default value"
                elif section == 3:
                    return "Output transformation"
                elif section == 4:
                    return "Delay"
        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )

from collections.abc import Sequence

from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QTableView
from caqtus.device.sequencer.configuration import ChannelConfiguration

from .channel_output_delegate import ChannelOutputDelegate
from .channels_model import SequencerChannelsModel


class SequencerChannelView(QTableView):
    def __init__(self, channels: Sequence[ChannelConfiguration], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.channel_model = SequencerChannelsModel(channels)
        self.setItemDelegateForColumn(1, ChannelOutputDelegate(self))
        self.verticalHeader().setMinimumSectionSize(-1)

    @property
    def channel_model(self) -> SequencerChannelsModel:
        return self._channel_model

    @channel_model.setter
    def channel_model(self, model: SequencerChannelsModel):
        self._channel_model = model
        self.setModel(self._channel_model)

    def set_channels(self, channels: Sequence[ChannelConfiguration]):
        self.channel_model.channels = tuple(channels)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        index = self.indexAt(event.pos())
        if index.isValid():
            self.edit(index)
        else:
            super().mouseDoubleClickEvent(event)

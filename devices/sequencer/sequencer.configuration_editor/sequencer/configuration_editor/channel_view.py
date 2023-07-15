from collections.abc import Sequence

from PyQt6.QtWidgets import QTableView

from sequencer.configuration import ChannelConfiguration
from .channels_model import SequencerChannelsModel
from .color_delegate import ColorDelegate
from .description_delegate import ChannelDescriptionDelegate
from .mapping_delegate import MappingDelegate


class SequencerChannelView(QTableView):
    def __init__(self, channels: Sequence[ChannelConfiguration], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.channel_model = SequencerChannelsModel(channels)
        self.setItemDelegateForColumn(0, ChannelDescriptionDelegate(self))
        self.setItemDelegateForColumn(1, ColorDelegate(self))

        self.setItemDelegateForColumn(3, MappingDelegate(self))

    @property
    def channel_model(self) -> SequencerChannelsModel:
        return self._model

    @channel_model.setter
    def channel_model(self, model: SequencerChannelsModel):
        self._model = model
        self.setModel(self._model)
        self.resizeColumnsToContents()

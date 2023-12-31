from collections.abc import Sequence

from PyQt6.QtWidgets import QTableView

from core.device.sequencer.configuration import ChannelConfiguration
from .channels_model import SequencerChannelsModel
from .color_delegate import ColorDelegate
from .description_delegate import ChannelDescriptionDelegate
from .mapping_delegate import MappingDelegate


class SequencerChannelView(QTableView):
    def __init__(self, channels: Sequence[ChannelConfiguration], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.channel_model = SequencerChannelsModel(channels)
        self._channel_delegate = ChannelDescriptionDelegate(self)
        self._color_delegate = ColorDelegate(self)
        self._mapping_delegate = MappingDelegate(self)
        self.setItemDelegateForColumn(0, self._channel_delegate)
        self.setItemDelegateForColumn(1, self._color_delegate)

        self.setItemDelegateForColumn(3, self._mapping_delegate)

        self.verticalHeader().setMinimumSectionSize(-1)

    @property
    def channel_model(self) -> SequencerChannelsModel:
        return self._channel_model

    @channel_model.setter
    def channel_model(self, model: SequencerChannelsModel):
        self._channel_model = model
        self.setModel(self._channel_model)

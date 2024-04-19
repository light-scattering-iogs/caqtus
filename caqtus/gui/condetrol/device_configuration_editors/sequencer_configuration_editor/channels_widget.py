from collections.abc import Sequence
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QGroupBox,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
)

from caqtus.device.sequencer import ChannelConfiguration


class SequencerChannelWidget(QWidget):
    """A widget that allow to edit the channel configurations of a sequencer.

    Attributes:
        channel_table: A table widget that shows the list of channels of the sequencer.
    """

    def __init__(
        self, channels: Sequence[ChannelConfiguration], parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        # We use a table widget and not a list widget because we want to have headers
        self.channel_table = QTableWidget(len(channels), 1, self)
        self.channel_table.horizontalHeader().setStretchLastSection(True)
        self.channel_table.horizontalHeader().hide()
        self.group_box = QGroupBox(self)
        self.channels = list(channels)

        layout = QHBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(self.channel_table)
        layout.addWidget(self.group_box)

        self._populate_channel_list()
        self.channel_table.currentItemChanged.connect(self._on_current_item_changed)
        self.channel_table.itemChanged.connect(self._on_item_changed)
        self.group_box.setVisible(False)

    def _populate_channel_list(self) -> None:
        self.channel_table.clear()
        for row, channel in enumerate(self.channels):
            item = QTableWidgetItem(channel.description)
            self.channel_table.setItem(row, 0, item)
        channel_labels = [self.channel_label(row) for row in range(len(self.channels))]
        self.channel_table.setVerticalHeaderLabels(channel_labels)

    def _on_current_item_changed(
        self, current: Optional[QTableWidgetItem], previous: Optional[QTableWidgetItem]
    ) -> None:
        self.set_preview_item(current)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item is self.channel_table.currentItem():
            self.set_preview_item(item)

    def set_preview_item(self, item: Optional[QTableWidgetItem]):
        if item is not None:
            self.group_box.setVisible(True)
            self.group_box.setTitle(item.text())
        else:
            self.group_box.setVisible(False)

    def channel_label(self, row: int) -> str:
        return str(row)

import copy
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
from .channel_output_editor import NewChannelOutputEditor


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
        self.channel_output_editor: Optional[NewChannelOutputEditor] = None
        self._populate_group_box()
        self.channels = list(channels)

        layout = QHBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(self.channel_table)
        layout.addWidget(self.group_box, 1)

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

    def _populate_group_box(self) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.group_box.setLayout(layout)

    def _on_current_item_changed(
        self, current: Optional[QTableWidgetItem], previous: Optional[QTableWidgetItem]
    ) -> None:
        if previous is not None:
            assert self.channel_output_editor is not None
            output = self.channel_output_editor.get_output()
            row = previous.row()
            self.channels[row].output = output
        self.set_preview_item(current)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item is self.channel_table.currentItem():
            self.set_preview_item(item)

    def set_preview_item(self, item: Optional[QTableWidgetItem]):
        if item is not None:
            self.group_box.setVisible(True)
            self.group_box.setTitle(item.text())
            row = item.row()
            channel = self.channels[row]
            previous_editor = None
            if self.channel_output_editor is not None:
                previous_editor = self.channel_output_editor
            self.channel_output_editor = NewChannelOutputEditor(channel.output, self)
            self.group_box.layout().addWidget(self.channel_output_editor)
            if previous_editor:
                previous_editor.deleteLater()
        else:
            self.group_box.setVisible(False)

    def channel_label(self, row: int) -> str:
        return str(row)

    def get_channel_configurations(self) -> list[ChannelConfiguration]:
        current_item = self.channel_table.currentItem()
        if current_item is not None:
            assert self.channel_output_editor is not None
            output = self.channel_output_editor.get_output()
            row = current_item.row()
            self.channels[row].output = output
        return copy.deepcopy(self.channels)

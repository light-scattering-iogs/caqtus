from PySide6.QtCore import QRect, QPoint, QSize
from PySide6.QtWidgets import QApplication

from caqtus.device.sequencer.channel_commands import ChannelOutput
from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor.channel_output_editor._channel_output_editor import (
    ChannelOutputGraph,
)


def screenshot_output(output: ChannelOutput, filename: str):
    editor = ChannelOutputGraph(output)
    editor.widget.show()
    rect = editor.zoom_to_nodes()
    max_width = QApplication.screens()[0].size().width()
    editor.widget.resize(max_width, int(rect.height() * max_width / rect.width()))
    editor.zoom_to_nodes()

    editor.widget.grab(QRect(QPoint(0, 0), QSize(-1, -1))).save(filename)

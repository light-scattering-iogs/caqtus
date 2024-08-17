from typing import Optional

from PySide6.QtCore import QRect, QPoint, QSize
from PySide6.QtWidgets import QApplication

from caqtus.device.sequencer.channel_commands import ChannelOutput
from caqtus.gui._common.NodeGraphQt import NodeGraph
from caqtus.gui.condetrol.device_configuration_editors.sequencer_configuration_editor.channel_output_editor._channel_output_editor import (
    ChannelOutputGraph,
    zoom_to_nodes,
)


def screenshot_output(output: Optional[ChannelOutput], filename: str):
    editor = ChannelOutputGraph(output)
    screenshot_graph(editor, filename)


def screenshot_node(node, filename: str):
    graph = NodeGraph()
    graph.add_node(node, selected=False)
    screenshot_graph(graph, filename)


def screenshot_graph(graph, filename: str):
    graph.widget.show()
    rect = zoom_to_nodes(graph)
    max_width = QApplication.screens()[0].size().width()
    graph.widget.resize(max_width, int(rect.height() * max_width / rect.width()))
    zoom_to_nodes(graph)
    graph.widget.grab(QRect(QPoint(0, 0), QSize(-1, -1))).save(filename)

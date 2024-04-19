from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout

from NodeGraphQt import NodeGraph
from caqtus.device.sequencer.configuration import ChannelOutput
from ._output_node import OutputNode


class NewChannelOutputEditor(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.graph = NodeGraph(self)
        self.graph.register_node(OutputNode)

        layout = QHBoxLayout(self)
        layout.addWidget(self.graph.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def set_output(self, output_label: str, channel_output: ChannelOutput) -> None:
        self.clear_graph()

        output_node = OutputNode()
        output_node.set_name()
        self.graph.add_node(output_node, selected=False, pos=[0, 0], push_undo=False)

    def clear_graph(self) -> None:
        for node in self.graph.all_nodes():
            self.graph.delete_node(node)

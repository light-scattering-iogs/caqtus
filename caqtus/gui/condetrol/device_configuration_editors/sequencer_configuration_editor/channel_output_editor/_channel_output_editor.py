import functools
from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout

from NodeGraphQt import NodeGraph, BaseNode
from caqtus.device.sequencer.configuration import ChannelOutput, Constant
from ._constant_node import ConstantNode
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

        node = self.build_node(channel_output)
        node.outputs()["out"].connect_to(output_node.inputs()["in"])

    def clear_graph(self) -> None:
        for node in self.graph.all_nodes():
            self.graph.delete_node(node)

    @functools.singledispatchmethod
    def build_node(self, channel_output: ChannelOutput) -> BaseNode:
        raise NotImplementedError

    @build_node.register
    def build_constant(self, constant: Constant) -> ConstantNode:
        node = ConstantNode()
        node.set_value(constant.value)
        self.graph.add_node(node, selected=False, push_undo=False)
        return node

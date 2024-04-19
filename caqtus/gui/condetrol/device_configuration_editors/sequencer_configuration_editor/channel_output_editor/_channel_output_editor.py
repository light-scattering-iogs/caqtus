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
        self.graph.register_node(ConstantNode)

        layout = QHBoxLayout(self)
        layout.addWidget(self.graph.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.output_node = OutputNode()
        self.graph.add_node(
            self.output_node, selected=False, pos=[0, 0], push_undo=False
        )

    def set_output(self, output_label: str, channel_output: ChannelOutput) -> None:
        self.clear_graph()

        node = self.build_node(channel_output)
        node.outputs()["out"].connect_to(self.output_node.inputs()["in"])

    def get_output(self) -> ChannelOutput:
        connected_node = self.output_node.connected_node()
        if connected_node is None:
            raise InvalidNodeConfigurationError(
                "No node is connected to the output node"
            )
        output = construct_output(connected_node)
        return output

    def clear_graph(self) -> None:
        for node in self.graph.all_nodes():
            if node is not self.output_node:
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


@functools.singledispatch
def construct_output(node) -> ChannelOutput:
    raise NotImplementedError


@construct_output.register
def construct_constant(node: ConstantNode) -> Constant:
    return Constant(value=node.get_value())


class InvalidNodeConfigurationError(ValueError):
    pass

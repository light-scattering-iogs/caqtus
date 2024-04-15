from PySide6 import QtWidgets

from NodeGraphQt import NodeGraph, BaseNode
from NodeGraphQt.constants import PortTypeEnum


class ConstantNode(BaseNode):

    __identifier__ = "sequencer_node"
    NODE_NAME = "Constant"

    def __init__(self):
        super().__init__()
        self.output_port = self.add_output("out", multi_output=False)
        self.output_port.add_accept_port_type(
            "in", PortTypeEnum.IN.value, "sequencer_node.OutputNode"
        )
        self.add_text_input("constant_value", "Value", "...")


class OutputNode(BaseNode):
    __identifier__ = "sequencer_node"
    NODE_NAME = "Output"

    def __init__(self):
        super().__init__()

        self.add_input("in", multi_input=False)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    graph = NodeGraph()

    graph.register_node(ConstantNode)
    graph.register_node(OutputNode)

    graph_widget = graph.widget
    graph_widget.show()

    node_a = ConstantNode()
    graph.add_node(node_a, selected=False)

    output_node = OutputNode()
    graph.add_node(output_node, selected=False)
    output_node.set_port_deletion_allowed(True)
    graph.delete_node(node_a)
    app.exec()

    print(node_a.output_port.connected_ports())

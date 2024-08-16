from typing import Optional

from caqtus.gui._common.NodeGraphQt import BaseNode
from caqtus.gui._common.NodeGraphQt.qgraphics.node_port_out import PortOutputNodeItem


class OutputNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node"

    def __init__(self, name: str):
        super().__init__(PortOutputNodeItem)
        self.input_port = self.add_input("in", display_name=False, multi_input=False)
        self.NODE_NAME = name

    def connected_node(self) -> Optional[BaseNode]:
        input_nodes = self.connected_input_nodes()[self.input_port]
        if len(input_nodes) == 0:
            return None
        elif len(input_nodes) == 1:
            return input_nodes[0]
        else:
            assert False, "There can't be multiple nodes connected to the input"

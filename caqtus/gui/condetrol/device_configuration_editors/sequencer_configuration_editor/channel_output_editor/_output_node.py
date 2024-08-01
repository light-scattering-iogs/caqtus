from typing import Optional

from caqtus.gui.common.NodeGraphQt import BaseNode


class OutputNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node"
    NODE_NAME = "Output"

    def __init__(self):
        super().__init__()
        self.input_port = self.add_input("in", display_name=False, multi_input=False)

    def connected_node(self) -> Optional[BaseNode]:
        input_nodes = self.connected_input_nodes()[self.input_port]
        if len(input_nodes) == 0:
            return None
        elif len(input_nodes) == 1:
            return input_nodes[0]
        else:
            assert False, "There can't be multiple nodes connected to the input"

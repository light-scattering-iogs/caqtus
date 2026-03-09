from typing import Optional

from caqtus.gui._common.NodeGraphQt import BaseNode


class LaneNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.source"
    NODE_NAME = "Lane"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.default_port = self.add_input("absent?", multi_input=False)
        self.add_text_input(
            "Lane",
            text="...",
            placeholder_text="lane name",
            tooltip="The name of the lane that should be ouput by this node.",
        )

    def set_lane_name(self, lane_name: str) -> None:
        self.set_property("Lane", lane_name)

    def get_lane_name(self) -> str:
        return str(self.get_property("Lane"))

    def get_default_node(self) -> Optional[BaseNode]:
        input_nodes = self.connected_input_nodes()[self.default_port]
        if len(input_nodes) == 0:
            return None
        elif len(input_nodes) == 1:
            return input_nodes[0]
        else:
            assert False, "There can't be multiple nodes connected to the input"

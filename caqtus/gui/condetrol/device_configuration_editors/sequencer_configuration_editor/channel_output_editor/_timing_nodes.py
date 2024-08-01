from typing import Optional

from caqtus.gui.common.NodeGraphQt import BaseNode
from caqtus.types.expression import Expression


class AdvanceNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.timing"
    NODE_NAME = "Advance"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.input_port = self.add_input("in", multi_input=False)
        self.add_text_input(
            "Advance",
            text="...",
            placeholder_text="...",
            tooltip="The duration by which to advance the channel.",
        )

    def set_advance(self, advance: Expression) -> None:
        self.set_property("Advance", str(advance))

    def get_advance(self) -> Expression:
        return Expression(str(self.get_property("Advance")))

    def get_input_node(self) -> Optional[BaseNode]:
        input_nodes = self.connected_input_nodes()[self.input_port]
        if len(input_nodes) == 0:
            return None
        elif len(input_nodes) == 1:
            return input_nodes[0]
        else:
            assert False, "There can't be multiple nodes connected to the input"


class BroadenLeftNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.timing"
    NODE_NAME = "Expand before"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.input_port = self.add_input("in", multi_input=False)
        self.add_text_input(
            "Width",
            text="...",
            placeholder_text="...",
            tooltip="The duration by which to broaden the pulses in the input.",
        )

    def set_width(self, broaden_left: Expression) -> None:
        self.set_property("Width", str(broaden_left))

    def get_width(self) -> Expression:
        return Expression(str(self.get_property("Width")))

    def get_input_node(self) -> Optional[BaseNode]:
        input_nodes = self.connected_input_nodes()[self.input_port]
        if len(input_nodes) == 0:
            return None
        elif len(input_nodes) == 1:
            return input_nodes[0]
        else:
            assert False, "There can't be multiple nodes connected to the input"

from caqtus.gui.common.NodeGraphQt import BaseNode
from caqtus.types.expression import Expression


class ConstantNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.source"
    NODE_NAME = "Constant"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.add_text_input(
            "Value",
            text="...",
            placeholder_text="value",
            tooltip="The output of this node is held constant during the whole shot.",
        )

    def set_value(self, expression: Expression) -> None:
        self.set_property("Value", str(expression))

    def get_value(self) -> Expression:
        return Expression(str(self.get_property("Value")))

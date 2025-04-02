from PySide6.QtWidgets import QLabel

from caqtus.gui._common.NodeGraphQt import BaseNode, NodeBaseWidget
from caqtus.gui.condetrol._icons import get_icon


class NotGateNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.logic"
    NODE_NAME = "Not"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.input_port = self.add_input("in", multi_input=False)
        node_widget = IconWidgetWrapper(get_icon("mdi6.gate-not"), self.view)
        self.add_custom_widget(node_widget, tab="Custom")

    def get_input_node(self) -> BaseNode | None:
        input_nodes = self.connected_input_nodes()[self.input_port]
        if len(input_nodes) == 0:
            return None
        elif len(input_nodes) == 1:
            return input_nodes[0]
        else:
            raise AssertionError("There can't be multiple nodes connected to the input")


class IconWidget(QLabel):
    def __init__(self, icon, parent=None):
        super().__init__(parent)
        self.setPixmap(icon.pixmap(64, 64))


class IconWidgetWrapper(NodeBaseWidget):
    """
    Wrapper that allows the widget to be added in a node object.
    """

    def __init__(self, icon, parent=None):
        super().__init__(parent)

        self.set_custom_widget(IconWidget(icon))

    def get_value(self):
        return None

    def set_value(self, text):
        pass

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


class AndGateNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.logic"
    NODE_NAME = "And"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.input_port_1 = self.add_input("in_1", multi_input=False)
        self.input_port_2 = self.add_input("in_2", multi_input=False)
        node_widget = IconWidgetWrapper(get_icon("mdi6.gate-and"), self.view)
        self.add_custom_widget(node_widget, tab="Custom")

    def get_input_nodes(self) -> tuple[BaseNode | None, BaseNode | None]:
        input_nodes_1 = self.connected_input_nodes()[self.input_port_1]
        input_nodes_2 = self.connected_input_nodes()[self.input_port_2]
        if len(input_nodes_1) == 0:
            input_node_1 = None
        elif len(input_nodes_1) == 1:
            input_node_1 = input_nodes_1[0]
        else:
            raise AssertionError("There can't be multiple nodes connected to the input")

        if len(input_nodes_2) == 0:
            input_node_2 = None
        elif len(input_nodes_2) == 1:
            input_node_2 = input_nodes_2[0]
        else:
            raise AssertionError("There can't be multiple nodes connected to the input")

        return input_node_1, input_node_2


class OrGateNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.logic"
    NODE_NAME = "Or"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.input_port_1 = self.add_input("in_1", multi_input=False)
        self.input_port_2 = self.add_input("in_2", multi_input=False)
        node_widget = IconWidgetWrapper(get_icon("mdi6.gate-or"), self.view)
        self.add_custom_widget(node_widget, tab="Custom")

    def get_input_nodes(self) -> tuple[BaseNode | None, BaseNode | None]:
        input_nodes_1 = self.connected_input_nodes()[self.input_port_1]
        input_nodes_2 = self.connected_input_nodes()[self.input_port_2]
        if len(input_nodes_1) == 0:
            input_node_1 = None
        elif len(input_nodes_1) == 1:
            input_node_1 = input_nodes_1[0]
        else:
            raise AssertionError("There can't be multiple nodes connected to the input")

        if len(input_nodes_2) == 0:
            input_node_2 = None
        elif len(input_nodes_2) == 1:
            input_node_2 = input_nodes_2[0]
        else:
            raise AssertionError("There can't be multiple nodes connected to the input")

        return input_node_1, input_node_2


class XorGateNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node.logic"
    NODE_NAME = "Xor"

    def __init__(self):
        super().__init__()
        self.add_output("out", multi_output=False, display_name=False)
        self.input_port_1 = self.add_input("in_1", multi_input=False)
        self.input_port_2 = self.add_input("in_2", multi_input=False)
        node_widget = IconWidgetWrapper(get_icon("mdi6.gate-xor"), self.view)
        self.add_custom_widget(node_widget, tab="Custom")

    def get_input_nodes(self) -> tuple[BaseNode | None, BaseNode | None]:
        input_nodes_1 = self.connected_input_nodes()[self.input_port_1]
        input_nodes_2 = self.connected_input_nodes()[self.input_port_2]
        if len(input_nodes_1) == 0:
            input_node_1 = None
        elif len(input_nodes_1) == 1:
            input_node_1 = input_nodes_1[0]
        else:
            raise AssertionError("There can't be multiple nodes connected to the input")

        if len(input_nodes_2) == 0:
            input_node_2 = None
        elif len(input_nodes_2) == 1:
            input_node_2 = input_nodes_2[0]
        else:
            raise AssertionError("There can't be multiple nodes connected to the input")

        return input_node_1, input_node_2


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

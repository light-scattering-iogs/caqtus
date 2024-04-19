import functools
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout

from NodeGraphQt import NodeGraph, BaseNode, NodesPaletteWidget
from caqtus.device.sequencer.configuration import (
    ChannelOutput,
    Constant,
    DeviceTrigger,
    LaneValues,
)
from ._constant_node import ConstantNode
from ._device_trigger_node import DeviceTriggerNode
from ._lane_node import LaneNode
from ._output_node import OutputNode


class NewChannelOutputEditor(QWidget):
    def __init__(self, channel_output: ChannelOutput, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.graph = NodeGraph(self)
        self.graph.register_node(ConstantNode)
        self.graph.register_node(DeviceTriggerNode)
        self.graph.register_node(LaneNode)
        self.nodes_tree = NodesPaletteWidget(node_graph=self.graph, parent=self)
        self.nodes_tree.set_category_label("caqtus.sequencer_node.source", "Source")

        layout = QVBoxLayout(self)
        layout.addWidget(self.graph.widget, 1)
        layout.addWidget(self.nodes_tree, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.output_node = OutputNode()
        self.graph.add_node(
            self.output_node, selected=False, pos=[0, 0], push_undo=False
        )

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

    @functools.singledispatchmethod
    def build_node(self, channel_output: ChannelOutput) -> BaseNode:
        raise NotImplementedError

    @build_node.register
    def build_constant(self, constant: Constant) -> ConstantNode:
        node = ConstantNode()
        node.set_value(constant.value)
        self.graph.add_node(node, selected=False, push_undo=False)
        return node

    @build_node.register
    def build_device_trigger_node(
        self, device_trigger: DeviceTrigger
    ) -> DeviceTriggerNode:
        node = DeviceTriggerNode()
        node.set_device_name(device_trigger.device_name)
        self.graph.add_node(node, selected=False, push_undo=False)
        if device_trigger.default is not None:
            default_node = self.build_node(device_trigger.default)
            default_node.outputs()["out"].connect_to(node.default_port)
        return node

    @build_node.register
    def build_lane_node(self, lane_values: LaneValues) -> LaneNode:
        node = LaneNode()
        node.set_lane_name(lane_values.lane)
        self.graph.add_node(node, selected=False, push_undo=False)
        if lane_values.default is not None:
            default_node = self.build_node(lane_values.default)
            default_node.outputs()["out"].connect_to(node.default_port)
        return node


@functools.singledispatch
def construct_output(node) -> ChannelOutput:
    raise NotImplementedError


@construct_output.register
def construct_constant(node: ConstantNode) -> Constant:
    return Constant(value=node.get_value())


@construct_output.register
def construct_device_trigger(node: DeviceTriggerNode) -> DeviceTrigger:
    device_name = node.get_device_name()
    default_node = node.get_default_node()
    if default_node is None:
        default = None
    else:
        default = construct_output(default_node)
    return DeviceTrigger(device_name=device_name, default=default)


@construct_output.register
def construct_lane_values(node: LaneNode) -> LaneValues:
    lane_name = node.get_lane_name()
    default_node = node.get_default_node()
    if default_node is None:
        default = None
    else:
        default = construct_output(default_node)
    return LaneValues(lane=lane_name, default=default)


class InvalidNodeConfigurationError(ValueError):
    pass

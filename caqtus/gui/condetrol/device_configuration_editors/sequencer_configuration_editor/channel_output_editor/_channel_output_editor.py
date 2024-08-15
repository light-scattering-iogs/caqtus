import functools
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout

from caqtus.device.sequencer.channel_commands import (
    ChannelOutput,
    Constant,
    DeviceTrigger,
    LaneValues,
    CalibratedAnalogMapping,
)
from caqtus.device.sequencer.channel_commands.timing import Advance, BroadenLeft
from caqtus.gui._common.NodeGraphQt import NodeGraph, BaseNode, NodesPaletteWidget
from ._analog_mapping_node import CalibratedAnalogMappingNode
from ._constant_node import ConstantNode
from ._device_trigger_node import DeviceTriggerNode
from ._lane_node import LaneNode
from ._output_node import OutputNode
from ._timing_nodes import AdvanceNode, BroadenLeftNode


class ChannelOutputEditor(QWidget):
    def __init__(self, channel_output: ChannelOutput, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.graph = NodeGraph(self)
        self.graph.register_node(ConstantNode)
        self.graph.register_node(DeviceTriggerNode)
        self.graph.register_node(LaneNode)
        self.graph.register_node(AdvanceNode)
        self.graph.register_node(CalibratedAnalogMappingNode)
        self.graph.register_node(BroadenLeftNode)
        self.nodes_tree = NodesPaletteWidget(node_graph=self.graph, parent=self)
        self.nodes_tree.set_category_label("caqtus.sequencer_node.source", "Source")
        self.nodes_tree.set_category_label("caqtus.sequencer_node.timing", "Timing")
        self.nodes_tree.set_category_label("caqtus.sequencer_node.mapping", "Mapping")

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
        self.graph.auto_layout_nodes()
        self.graph.set_pipe_collision(True)
        self.graph.clear_undo_stack()

    def get_output(self) -> ChannelOutput:
        connected_node = self.output_node.connected_node()
        if connected_node is None:
            raise MissingInputError("No node is connected to the output node")
        output = construct_output(connected_node)
        return output

    @functools.singledispatchmethod
    def build_node(self, channel_output: ChannelOutput) -> BaseNode:
        raise NotImplementedError(f"Can't build node from {type(channel_output)}")

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

    @build_node.register
    def build_advance_node(self, advance: Advance) -> AdvanceNode:
        node = AdvanceNode()
        node.set_advance(advance.advance)
        self.graph.add_node(node, selected=False, push_undo=False)
        input_node = self.build_node(advance.input_)
        input_node.outputs()["out"].connect_to(node.input_port)
        return node

    @build_node.register
    def build_analog_mapping_node(
        self, analog_mapping: CalibratedAnalogMapping
    ) -> CalibratedAnalogMappingNode:
        node = CalibratedAnalogMappingNode()
        node.set_units(analog_mapping.input_units, analog_mapping.output_units)
        node.set_data_points(analog_mapping.measured_data_points)
        self.graph.add_node(node, selected=False, push_undo=False)
        input_node = self.build_node(analog_mapping.input_)
        input_node.outputs()["out"].connect_to(node.input_port)
        return node

    @build_node.register
    def build_broaden_left_node(self, broaden_left: BroadenLeft) -> BroadenLeftNode:
        node = BroadenLeftNode()
        node.set_width(broaden_left.width)
        self.graph.add_node(node, selected=False, push_undo=False)
        input_node = self.build_node(broaden_left.input_)
        input_node.outputs()["out"].connect_to(node.input_port)
        return node


@functools.singledispatch
def construct_output(node) -> ChannelOutput:
    raise NotImplementedError(f"Cant construct output from {type(node)}")


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


@construct_output.register
def construct_advance(node: AdvanceNode) -> Advance:
    advance = node.get_advance()
    input_node = node.get_input_node()
    if input_node is None:
        raise MissingInputError(f"Advance node {node.name()} must have an input node")
    else:
        input_ = construct_output(input_node)
    return Advance(advance=advance, input_=input_)


@construct_output.register
def construct_analog_mapping(
    node: CalibratedAnalogMappingNode,
) -> CalibratedAnalogMapping:
    input_node = node.get_input_node()
    if input_node is None:
        raise MissingInputError(
            f"Analog mapping node {node.name()} must have an input node"
        )
    else:
        input_ = construct_output(input_node)
    input_units, output_units = node.get_units()
    return CalibratedAnalogMapping(
        input_=input_,
        input_units=input_units,
        output_units=output_units,
        measured_data_points=tuple(node.get_data_points()),
    )


@construct_output.register
def construct_broaden_left(node: BroadenLeftNode) -> BroadenLeft:
    width = node.get_width()
    input_node = node.get_input_node()
    if input_node is None:
        raise MissingInputError(
            f"Broaden left node {node.name()} must have an input node"
        )
    else:
        input_ = construct_output(input_node)
    return BroadenLeft(width=width, input_=input_)


class InvalidNodeConfigurationError(ValueError):
    pass


class MissingInputError(InvalidNodeConfigurationError):
    pass

import functools
from typing import Optional

from PySide6 import QtCore
from PySide6.QtCore import QRect
from PySide6.QtGui import QKeySequence, QAction
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

        self.graph = ChannelOutputGraph(channel_output)

        self.nodes_palette = NodesPaletteWidget(node_graph=self.graph, parent=self)
        self.nodes_palette.set_category_label("caqtus.sequencer_node.source", "Source")
        self.nodes_palette.set_category_label("caqtus.sequencer_node.timing", "Timing")
        self.nodes_palette.set_category_label(
            "caqtus.sequencer_node.mapping", "Mapping"
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.graph.widget, 1)
        layout.addWidget(self.nodes_palette, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.graph.resize()

    def get_output(self) -> ChannelOutput:
        return self.graph.get_output()


class ChannelOutputGraph(NodeGraph):
    def __init__(self, channel_output: Optional[ChannelOutput]):
        super().__init__()
        self.register_node(ConstantNode)
        self.register_node(DeviceTriggerNode)
        self.register_node(LaneNode)
        self.register_node(AdvanceNode)
        self.register_node(CalibratedAnalogMappingNode)
        self.register_node(BroadenLeftNode)

        self.output_node = OutputNode("out")
        self.add_node(self.output_node, selected=False, pos=[0, 0], push_undo=False)

        if channel_output:
            node = self.build_node(channel_output)
            node.outputs()["out"].connect_to(self.output_node.inputs()["in"])
        self.auto_layout_nodes(down_stream=False)
        self.set_pipe_collision(True)
        self.clear_undo_stack()
        self.zoom_to_nodes()

        self.auto_layout_action = QAction(self.widget)
        self.auto_layout_action.setShortcut(QKeySequence("Ctrl+L"))
        self.auto_layout_action.triggered.connect(self._on_refit)
        self.widget.addAction(self.auto_layout_action)

    def _on_refit(self):
        self.auto_layout_nodes()
        self.zoom_to_nodes()

    def zoom_to_nodes(self) -> QRect:
        """Zoom the graph view to fit all nodes."""

        return zoom_to_nodes(self)

    def resize(self) -> None:
        """Resize the graph view to fit all nodes and zoom in."""

        self.fit_to_selection()
        self.set_zoom(2)

    def get_output(self) -> ChannelOutput:
        """Return the channel output represented by the graph.

        Raises:
            InvalidNodeConfigurationError: If the graph is not correctly configured.
        """

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
        self.add_node(node, selected=False, push_undo=False)
        return node

    @build_node.register
    def build_device_trigger_node(
        self, device_trigger: DeviceTrigger
    ) -> DeviceTriggerNode:
        node = DeviceTriggerNode()
        node.set_device_name(device_trigger.device_name)
        self.add_node(node, selected=False, push_undo=False)
        if device_trigger.default is not None:
            default_node = self.build_node(device_trigger.default)
            default_node.outputs()["out"].connect_to(node.default_port)
        return node

    @build_node.register
    def build_lane_node(self, lane_values: LaneValues) -> LaneNode:
        node = LaneNode()
        node.set_lane_name(lane_values.lane)
        self.add_node(node, selected=False, push_undo=False)
        if lane_values.default is not None:
            default_node = self.build_node(lane_values.default)
            default_node.outputs()["out"].connect_to(node.default_port)
        return node

    @build_node.register
    def build_advance_node(self, advance: Advance) -> AdvanceNode:
        node = AdvanceNode()
        node.set_advance(advance.advance)
        self.add_node(node, selected=False, push_undo=False)
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
        self.add_node(node, selected=False, push_undo=False)
        input_node = self.build_node(analog_mapping.input_)
        input_node.outputs()["out"].connect_to(node.input_port)
        return node

    @build_node.register
    def build_broaden_left_node(self, broaden_left: BroadenLeft) -> BroadenLeftNode:
        node = BroadenLeftNode()
        node.set_width(broaden_left.width)
        self.add_node(node, selected=False, push_undo=False)
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


def zoom_to_nodes(graph: NodeGraph) -> QRect:
    all_nodes = graph.all_nodes()

    group = graph.scene().createItemGroup([node.view for node in all_nodes])
    rect = group.boundingRect().adjusted(-10, -10, 10, 10)
    graph.scene().destroyItemGroup(group)

    graph.viewer().setSceneRect(rect)
    graph.viewer().fitInView(rect, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
    return rect

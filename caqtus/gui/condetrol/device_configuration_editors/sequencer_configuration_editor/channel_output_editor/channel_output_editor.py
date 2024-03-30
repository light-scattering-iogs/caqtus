import copy
import functools
from typing import Optional

from PySide6.QtCore import Qt, QLineF
from PySide6.QtGui import QPen, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QWidget,
    QGraphicsSceneMouseEvent,
    QMenu,
    QGraphicsLineItem,
)

from caqtus.device.sequencer import ChannelConfiguration
from caqtus.gui.common.qtutil import temporary_widget
from .build_blocks import create_functional_blocks
from .build_configuration import build_output, MissingInputError
from .connection import (
    ConnectionLink,
    ConnectionPoint,
    OutputConnectionPoint,
    InputConnectionPoint,
)
from .functional_blocks import (
    TimeLaneBlock,
    AnalogMappingBlock,
    FunctionalBlock,
    HoldBlock,
    DeviceTriggerBlock,
    AdvanceBlock,
    DelayBlock,
)


class ChannelOutputEditor(QGraphicsView):
    def __init__(
        self,
        channel_label: str,
        channel_configuration: ChannelConfiguration,
        parent: Optional[QWidget] = None,
    ):
        self._scene = ChannelOutputScene(channel_label, channel_configuration, parent)
        super().__init__(self._scene, parent)
        self.reposition_blocks = QShortcut(QKeySequence("Ctrl+L"), self)
        self.reposition_blocks.activated.connect(self.on_reposition_blocks)

    def on_reposition_blocks(self):
        self._scene.reposition_child_blocks(self._scene.channel_output)

    def get_channel_configuration(self) -> ChannelConfiguration:
        return self._scene.build_channel_configuration()


class ChannelOutputScene(QGraphicsScene):
    def __init__(
        self,
        channel_label: str,
        channel_configuration: ChannelConfiguration,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.channel_output = create_functional_blocks(
            channel_label, channel_configuration
        )
        self.channel_configuration = channel_configuration
        self.add_block(self.channel_output)
        self.reposition_child_blocks(self.channel_output)

        # This object is used to store the line and the initial connection point when
        # the user starts dragging a line to connect two blocks.
        self._line_and_initial_connection: Optional[
            tuple[QGraphicsLineItem, ConnectionPoint]
        ] = None

    def add_block(self, block: FunctionalBlock) -> None:
        """Recursively add a block and all its input blocks to the scene."""

        self.addItem(block)
        for connection in block.input_connections:
            link = connection.link
            if link is not None:
                self.addItem(link)
                self.add_block(link.output_connection.block)

    def _is_user_dragging_line(self) -> bool:
        return self._line_and_initial_connection is not None

    def _clear_user_dragging_line(self) -> None:
        assert self._line_and_initial_connection is not None
        line_item = self._line_and_initial_connection[0]
        self.removeItem(line_item)
        self._line_and_initial_connection = None

    def get_line_item(self) -> Optional[QGraphicsLineItem]:
        return (
            self._line_and_initial_connection[0]
            if self._line_and_initial_connection
            else None
        )

    def get_initial_connection_point(self) -> Optional[ConnectionPoint]:
        return (
            self._line_and_initial_connection[1]
            if self._line_and_initial_connection
            else None
        )

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            with temporary_widget(QMenu()) as menu:
                add_source_block = menu.addMenu("Add source block")
                add_time_lane_action = add_source_block.addAction("time lane")
                add_time_lane_action.triggered.connect(
                    functools.partial(self.add_time_lane, event.scenePos())
                )
                add_hold_action = add_source_block.addAction("hold")
                add_hold_action.triggered.connect(
                    functools.partial(self.add_hold_block, event.scenePos())
                )
                add_device_trigger_action = add_source_block.addAction("device trigger")
                add_device_trigger_action.triggered.connect(
                    functools.partial(self.add_device_trigger_block, event.scenePos())
                )
                action = menu.addAction("Add analog mapping")
                action.triggered.connect(
                    functools.partial(self.add_analog_mapping, event.scenePos())
                )
                add_timing_block = menu.addMenu("Add timing block")
                add_advance_action = add_timing_block.addAction("advance")
                add_advance_action.triggered.connect(
                    functools.partial(self.add_advance_block, event.scenePos())
                )
                add_delay_action = add_timing_block.addAction("delay")
                add_delay_action.triggered.connect(
                    functools.partial(self.add_delay_block, event.scenePos())
                )
                menu.exec(event.screenPos())
                return
        elif event.button() == Qt.MouseButton.LeftButton:
            items_at_click = self.items(event.scenePos())
            if len(items_at_click) != 0:
                highest_item = items_at_click[0]
                if isinstance(highest_item, ConnectionPoint):
                    line = QLineF(
                        highest_item.link_position(), highest_item.link_position()
                    )
                    line_item = QGraphicsLineItem(line)
                    line_item.setPen(QPen(Qt.GlobalColor.white, 1))
                    self._line_and_initial_connection = (line_item, highest_item)
                    self.addItem(line_item)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._is_user_dragging_line():
            line_item = self.get_line_item()
            assert line_item is not None
            new_line = QLineF(line_item.line().p1(), event.scenePos())
            line_item.setLine(new_line)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._is_user_dragging_line():
            line_item = self.get_line_item()
            assert line_item is not None
            items_at_release = self.items(line_item.line().p2())
            if len(items_at_release):
                # The dragged line is often the first item in the list of items at the
                # release point, so we remove it.
                if items_at_release[0] is line_item:
                    items_at_release = items_at_release[1:]
            initial_connection_point = self.get_initial_connection_point()
            assert initial_connection_point is not None
            self._clear_user_dragging_line()

            if len(items_at_release):
                highest_item = items_at_release[0]
                if isinstance(highest_item, ConnectionPoint):
                    final_connection_point = highest_item
                    link = self.create_link(
                        initial_connection_point, final_connection_point
                    )
                    if link is not None:
                        self.remove_potential_link(initial_connection_point)
                        self.remove_potential_link(final_connection_point)
                        initial_connection_point.link = link
                        final_connection_point.link = link
                        self.addItem(link)
                    return
        else:
            super().mouseReleaseEvent(event)

    def remove_potential_link(self, connection: ConnectionPoint) -> None:
        if (link := connection.link) is not None:
            link.input_connection.link = None
            link.output_connection.link = None
            self.removeItem(link)

    @staticmethod
    def create_link(
        initial_connection: ConnectionPoint, final_connection: ConnectionPoint
    ) -> Optional[ConnectionLink]:
        """Attempts to create a link between two connection points.

        This will check is on of the connection points is an input and the other is an
        output.
        If that is the case, a link between the two connection points is created and
        returned.
        If not, None is returned.
        """

        if isinstance(initial_connection, OutputConnectionPoint):
            if isinstance(final_connection, InputConnectionPoint):
                link = ConnectionLink(
                    input_connection=final_connection,
                    output_connection=initial_connection,
                )
                return link
            else:
                return None
        elif isinstance(initial_connection, InputConnectionPoint):
            if isinstance(final_connection, OutputConnectionPoint):
                link = ConnectionLink(
                    input_connection=initial_connection,
                    output_connection=final_connection,
                )
                return link
            else:
                return None
        return None

    def add_analog_mapping(self, pos):
        block = AnalogMappingBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

    def add_time_lane(self, pos) -> None:
        block = TimeLaneBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

    def add_hold_block(self, pos) -> None:
        block = HoldBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

    def add_device_trigger_block(self, pos) -> None:
        block = DeviceTriggerBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

    def add_advance_block(self, pos) -> None:
        block = AdvanceBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

    def add_delay_block(self, pos) -> None:
        block = DelayBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

    def reposition_child_blocks(self, block: FunctionalBlock):
        for connection in block.input_connections:
            link = connection.link
            if link is not None:
                input_block = link.output_connection.block
                input_block.setX(block.x() - input_block.boundingRect().width() - 100)
                self.reposition_child_blocks(input_block)

    def build_channel_configuration(self) -> ChannelConfiguration:
        """Construct the channel configuration from the blocks in the scene.

        Raises:
            OutputConstructionError: If the output of the channel output block cannot be
            constructed from the blocks in the scene.
        """

        channel_configuration = copy.deepcopy(self.channel_configuration)
        link = self.channel_output.input_connections[0].link
        if link is None:
            raise MissingInputError("The channel output block has no input")
        previous_block = link.output_connection.block
        channel_configuration.output = build_output(previous_block)
        return channel_configuration

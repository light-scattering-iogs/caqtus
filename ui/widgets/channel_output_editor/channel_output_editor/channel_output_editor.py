import functools
from typing import Optional

from PySide6.QtCore import Qt, QLineF
from PySide6.QtGui import QPen
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QWidget,
    QGraphicsSceneMouseEvent,
    QMenu,
    QGraphicsLineItem,
)

from core.device.sequencer import ChannelConfiguration
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
)
from .build_blocks import create_functional_blocks


class ChannelOutputEditor(QGraphicsView):
    def __init__(
        self,
        channel_label: str,
        channel_configuration: ChannelConfiguration,
        parent: Optional[QWidget] = None,
    ):
        self._scene = ChannelOutputScene(channel_label, channel_configuration, parent)
        super().__init__(self._scene, parent)


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
        self.add_block(self.channel_output)
        # self.addItem(self.channel_output)

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
            menu = QMenu()
            action = menu.addAction("Add time lane")
            action.triggered.connect(
                functools.partial(self.add_time_lane, event.scenePos())
            )
            action = menu.addAction("Add analog mapping")
            action.triggered.connect(
                functools.partial(self.add_analog_mapping, event.scenePos())
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

    def add_time_lane(self, pos):
        block = TimeLaneBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

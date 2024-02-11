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

from .calibrated_analog_mapping_item import AnalogMappingBlock
from .item_container import (
    ChannelOutputBlock,
    TimeLaneBlock,
    ConnectionPoint,
)
from .connection import ConnectionLink


class ChannelOutputEditor(QGraphicsView):
    def __init__(self, parent: Optional[QWidget] = None):
        self._scene = ChannelOutputScene("421 cell \\ AOM", parent)
        super().__init__(self._scene, parent)


class ChannelOutputScene(QGraphicsScene):
    def __init__(self, channel_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.channel_output = ChannelOutputBlock(channel_label)
        self.addItem(self.channel_output)

        # This object is used to store the line and the initial connection point when
        # the user starts dragging a line to connect two blocks.
        self._line_and_initial_connection: Optional[
            tuple[QGraphicsLineItem, ConnectionPoint]
        ] = None

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
                if items_at_release[0] is self.get_line_item():
                    items_at_release = items_at_release[1:]
            initial_connection = self.get_initial_connection_point()
            assert initial_connection is not None
            self._clear_user_dragging_line()

            if len(items_at_release):
                highest_item = items_at_release[0]
                if isinstance(highest_item, ConnectionPoint):
                    link = ConnectionLink(initial_connection, highest_item)
                    self.addItem(link)
                    initial_connection.link = link
                    highest_item.link = link
                    return
        else:
            super().mouseReleaseEvent(event)

    def add_analog_mapping(self, pos):
        block = AnalogMappingBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

    def add_time_lane(self, pos):
        block = TimeLaneBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

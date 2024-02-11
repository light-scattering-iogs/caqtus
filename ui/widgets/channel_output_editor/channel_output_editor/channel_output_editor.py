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
from .item_container import ChannelOutputBlock, TimeLaneBlock, ConnectionPoint


class ChannelOutputEditor(QGraphicsView):
    def __init__(self, parent: Optional[QWidget] = None):
        self._scene = ChannelOutputScene("421 cell \\ AOM", parent)
        super().__init__(self._scene, parent)


class ChannelOutputScene(QGraphicsScene):
    def __init__(self, channel_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.channel_output = ChannelOutputBlock(channel_label)
        self.addItem(self.channel_output)

        # A line that is drawn when the user is linking two connections
        self.line: Optional[QGraphicsLineItem] = None

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
                    self.line = QGraphicsLineItem(
                        QLineF(
                            highest_item.link_position(), highest_item.link_position()
                        )
                    )
                    self.line.setPen(QPen(Qt.GlobalColor.white, 1))
                    self.addItem(self.line)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.line is not None:
            new_line = QLineF(self.line.line().p1(), event.scenePos())
            self.line.setLine(new_line)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.line is not None:
            self.removeItem(self.line)
            self.line = None
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

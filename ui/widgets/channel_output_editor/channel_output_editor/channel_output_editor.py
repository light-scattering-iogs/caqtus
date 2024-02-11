import functools
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QWidget,
    QGraphicsSceneMouseEvent,
    QMenu,
)

from .calibrated_analog_mapping_item import AnalogMappingBlock
from .item_container import ChannelOutputBlock, TimeLaneBlock


class ChannelOutputEditor(QGraphicsView):
    def __init__(self, parent: Optional[QWidget] = None):
        self._scene = ChannelOutputScene("421 cell \\ AOM", parent)
        super().__init__(self._scene, parent)


class ChannelOutputScene(QGraphicsScene):
    def __init__(self, channel_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.channel_output = ChannelOutputBlock(channel_label)
        self.addItem(self.channel_output)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        super().mousePressEvent(event)
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

    def add_analog_mapping(self, pos):
        block = AnalogMappingBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

    def add_time_lane(self, pos):
        block = TimeLaneBlock()
        self.addItem(block)
        block.setPos(pos.x(), pos.y())

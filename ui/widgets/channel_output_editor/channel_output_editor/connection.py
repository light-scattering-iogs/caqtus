from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
)


class ConnectionPoint(QGraphicsEllipseItem):
    """A connection point for a :class:`FunctionalBlock`."""

    def __init__(self):
        super().__init__(0, 0, 10, 10)

        self.setBrush(QColor(0, 255, 0))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.link: Optional[ConnectionLink] = None

    def setPos(self, x, y):
        super().setPos(x - 5, y)
        self.update()

    def link_position(self):
        """Return the center of the connection point"""
        rect = self.rect()
        return self.scenePos() + rect.center()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged:
            if self.link is not None:
                self.link.update_position()
        return super().itemChange(change, value)


class ConnectionLink(QGraphicsLineItem):
    """A link between two connection points."""

    def __init__(self, start: ConnectionPoint, end: ConnectionPoint):
        super().__init__(
            start.link_position().x(),
            start.link_position().y(),
            end.link_position().x(),
            end.link_position().y(),
        )
        self.setPen(QPen(Qt.GlobalColor.white, 1))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.start_connection = start
        self.end_connection = end

    def update_position(self) -> None:
        """Update the position of the link to follow the connection points."""

        self.setLine(
            self.start_connection.link_position().x(),
            self.start_connection.link_position().y(),
            self.end_connection.link_position().x(),
            self.end_connection.link_position().y(),
        )

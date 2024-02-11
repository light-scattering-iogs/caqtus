from __future__ import annotations

from typing import Optional, Any, TYPE_CHECKING

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
)

if TYPE_CHECKING:
    from .functional_blocks import FunctionalBlock


class ConnectionPoint(QGraphicsEllipseItem):
    """A connection point for a :class:`FunctionalBlock`."""

    def __init__(self, parent: FunctionalBlock):
        super().__init__(0, 0, 10, 10, parent=parent)

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.link = None
        self.block = parent

    @property
    def link(self) -> Optional[ConnectionLink]:
        return self._link

    @link.setter
    def link(self, link: Optional[ConnectionLink]) -> None:
        if hasattr(self, "_link"):
            if self._link is not None and link is not None:
                raise ValueError("The connection point is already linked")
        self._link = link
        if link is not None:
            self.setBrush(Qt.GlobalColor.green)
        else:
            self.setBrush(Qt.GlobalColor.red)

    def setPos(self, x, y) -> None:
        super().setPos(x - 5, y)
        self.update()

    def link_position(self) -> QPointF:
        """Return the point where the link should connect to."""

        rect = self.rect()
        return self.scenePos() + rect.center()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemScenePositionHasChanged:
            if self.link is not None:
                self.link.update_position()
        return super().itemChange(change, value)


class InputConnectionPoint(ConnectionPoint):
    """A connection point for an input a functional block."""

    pass


class OutputConnectionPoint(ConnectionPoint):
    """A connection point for the output of a functional block."""

    pass


class ConnectionLink(QGraphicsLineItem):
    """A link between two connection points.

    The link must connect an output connection point to an input connection point.
    It cannot connect two input connection points or two output connection points.
    """

    def __init__(
        self,
        *,
        input_connection: InputConnectionPoint,
        output_connection: OutputConnectionPoint,
    ):
        if not isinstance(input_connection, InputConnectionPoint):
            raise ValueError("The input_connection must be an InputConnectionPoint")
        if not isinstance(output_connection, OutputConnectionPoint):
            raise ValueError("The output_connection must be an OutputConnectionPoint")
        super().__init__(
            input_connection.link_position().x(),
            input_connection.link_position().y(),
            output_connection.link_position().x(),
            output_connection.link_position().y(),
        )
        self.setPen(QPen(Qt.GlobalColor.white, 1))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.input_connection = input_connection
        self.output_connection = output_connection

    def update_position(self) -> None:
        """Update the position of the link to follow the connection points."""

        self.setLine(
            self.input_connection.link_position().x(),
            self.input_connection.link_position().y(),
            self.output_connection.link_position().x(),
            self.output_connection.link_position().y(),
        )

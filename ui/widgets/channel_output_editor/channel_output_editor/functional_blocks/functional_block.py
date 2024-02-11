from typing import Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsItem,
)

from ..connection import InputConnectionPoint, OutputConnectionPoint


class FunctionalBlock(QGraphicsRectItem):
    """A block item that represents a function.

    A functional block is a block that represents a function and can be drawn on a
    QGraphicsScene.
    It has input connections points that are used to feed function arguments.
    It also has an (optional) output connection that can be used to connect the result
    of the function to another block.
    Links between blocks can be created to represent the flow of data between blocks.
    It contains a QGraphicsItem that represents the function itself and can be used to
    display and edit various function parameters.
    """

    def __init__(
        self,
        number_input_connections: int,
        has_output_connection: bool = True,
        parent: Optional[QGraphicsItem] = None,
    ):
        super().__init__(0, 0, 100, 100, parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setBrush(QColor(100, 100, 100))
        self.setPen(QColor(255, 255, 255))

        self.input_connections: list[InputConnectionPoint] = []
        for i in range(number_input_connections):
            connection = InputConnectionPoint(self)
            connection.setZValue(2)
            self.input_connections.append(connection)

        self.output_connection: Optional[OutputConnectionPoint] = None
        if has_output_connection:
            self.output_connection = OutputConnectionPoint(self)
            self.output_connection.setZValue(2)
        self.update_connection_positions()

    def set_item(self, item: QGraphicsItem) -> None:
        """Set the item that will be displayed inside the functional block.

        The item will be displayed inside the functional block and will be used to
        represent the function itself.
        The functional block takes ownership of the item.
        """

        item.setParentItem(self)
        # The item might not be a rectangle, so we pick the bounding rectangle of the
        # item to set the size of the functional block.
        rect = item.boundingRect()
        self.setRect(0, 0, rect.width() + 2, rect.height() + 2)
        item.setZValue(1)
        item.setPos(1, 1)

    def setRect(self, *args, **kwargs):
        super().setRect(*args, **kwargs)
        self.update_connection_positions()

    def update_connection_positions(self):
        height = self.rect().height()
        width = self.rect().width()
        for i, input_connection in enumerate(self.input_connections):
            vertical_spacing = height / (len(self.input_connections) + 1)
            input_connection.setPos(0, (i + 1) * vertical_spacing - 5)
        if self.output_connection is not None:
            self.output_connection.setPos(width, height / 2 - 5)

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QPen
from PySide6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsItem,
    QGraphicsEllipseItem,
    QLineEdit,
    QGraphicsProxyWidget,
    QLabel,
    QWidget,
    QFormLayout,
    QGraphicsLineItem,
)


class FunctionalBlock(QGraphicsRectItem):
    """A block item that represents a function.

    A functional block is a block that represents a function. It has input connections
    that are used to feed function arguments and an (optional) output connection that
    can be used to connect the result of the function to another block.
    """

    def __init__(
        self,
        number_input_connections: int,
        has_output_connection: bool = True,
        parent=None,
    ):
        super().__init__(0, 0, 100, 100, parent)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setBrush(QColor(100, 100, 100))
        self.setPen(QColor(255, 255, 255))

        self.input_connections: list[ConnectionPoint] = []
        for i in range(number_input_connections):
            connection = ConnectionPoint()
            connection.setParentItem(self)
            connection.setZValue(2)
            self.input_connections.append(connection)

        self.output_connection: Optional[ConnectionPoint] = None
        if has_output_connection:
            self.output_connection = ConnectionPoint()
            self.output_connection.setParentItem(self)
            self.output_connection.setZValue(2)
        self.update_connection_positions()

    def set_item(self, item: QGraphicsItem):
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


class ChannelOutputBlock(FunctionalBlock):
    """The output"""

    def __init__(self, output_name: str, parent: Optional[QGraphicsItem] = None):
        super().__init__(
            number_input_connections=1, has_output_connection=False, parent=parent
        )
        widget = QWidget()
        layout = QFormLayout()
        layout.addRow("Channel 0", QLabel(output_name))
        widget.setLayout(layout)
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(widget)
        self.set_item(proxy)


class TimeLaneBlock(FunctionalBlock):
    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(
            number_input_connections=0, has_output_connection=True, parent=parent
        )

        widget = QWidget()
        layout = QFormLayout()

        layout.addRow("Time lane", QLineEdit())
        widget.setLayout(layout)

        pal = QPalette()

        pal.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)

        widget.setAutoFillBackground(True)
        widget.setPalette(pal)

        proxy = QGraphicsProxyWidget()
        proxy.setWidget(widget)

        self.set_item(proxy)

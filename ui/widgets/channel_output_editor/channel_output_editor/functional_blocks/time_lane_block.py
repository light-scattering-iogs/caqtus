from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QGraphicsItem,
    QWidget,
    QFormLayout,
    QGraphicsProxyWidget,
    QLineEdit,
)

from .functional_block import FunctionalBlock


class TimeLaneBlock(FunctionalBlock):
    """A block representing values fed by evaluating a time lane.

    This block is a leftmost block in the scene and has no input connections.
    """

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

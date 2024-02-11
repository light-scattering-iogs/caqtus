from typing import Optional

from PySide6.QtWidgets import (
    QGraphicsItem,
    QWidget,
    QFormLayout,
    QGraphicsProxyWidget,
    QLineEdit,
)

from core.types.expression import Expression
from .functional_block import FunctionalBlock


class HoldBlock(FunctionalBlock):
    """A block representing a value held constant during the shot.

    This block is a leftmost block in the scene and has no input connections.
    It presents a line edit to input the value of the constant.
    """

    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(
            number_input_connections=0, has_output_connection=True, parent=parent
        )

        proxy = QGraphicsProxyWidget()
        widget = QWidget()
        layout = QFormLayout()
        widget.setLayout(layout)
        self.line_edit = QLineEdit()
        layout.addRow("Hold", self.line_edit)
        proxy.setWidget(widget)
        self.set_item(proxy)

    def set_value(self, value: Expression) -> None:
        self.line_edit.setText(str(value))

    def get_value(self) -> Expression:
        return Expression(self.line_edit.text())

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


class TimeLaneBlock(FunctionalBlock):
    """A block representing values fed by evaluating a time lane.

    This block is a leftmost block in the scene and has no input connections.
    It presents a line edit to input the name of the time lane it represents.
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
        layout.addRow("Time lane", self.line_edit)
        self.default_value = QLineEdit()
        self.default_value.setPlaceholderText("None")
        layout.addRow("if absent", self.default_value)
        proxy.setWidget(widget)
        self.set_item(proxy)

    def set_lane_name(self, lane: str) -> None:
        self.line_edit.setText(lane)

    def get_lane_name(self) -> str:
        return self.line_edit.text()

    def set_default_value(self, value: Optional[Expression]) -> None:
        if value is None:
            self.default_value.clear()
        else:
            self.default_value.setText(str(value))

    def get_default_value(self) -> Optional[Expression]:
        if self.default_value.text() == "":
            return None
        return Expression(self.default_value.text())

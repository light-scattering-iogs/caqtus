from typing import Optional

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
    It presents a line edit to input the name of the time lane it represents.
    """

    def __init__(self, parent: Optional[QGraphicsItem] = None):
        super().__init__(
            number_input_connections=0, has_output_connection=True, parent=parent
        )

        widget = QWidget()
        layout = QFormLayout(widget)
        widget.setLayout(layout)
        self.line_edit = QLineEdit(widget)
        layout.addRow("Time lane", self.line_edit)

        proxy = QGraphicsProxyWidget()
        proxy.setWidget(widget)

        self.set_item(proxy)

    def set_lane_name(self, lane: str) -> None:
        self.line_edit.setText(lane)

    def get_lane_name(self) -> str:
        return self.line_edit.text()

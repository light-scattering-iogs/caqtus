from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGraphicsProxyWidget,
    QWidget,
    QFormLayout,
    QLabel,
    QLineEdit,
)

from caqtus.types.expression import Expression
from .functional_block import FunctionalBlock


class AdvanceBlock(FunctionalBlock):
    """Represents a block that shifts the input signal to past times."""

    def __init__(self, parent=None):
        super().__init__(
            number_input_connections=1, has_output_connection=True, parent=parent
        )

        proxy = QGraphicsProxyWidget()
        widget = QWidget()
        widget.setLayout(layout := QFormLayout(widget))
        label = QLabel("<i>y(t) = x(t + τ)</i>", widget)
        layout.addRow("Advance", label)
        self.advance_line_edit = QLineEdit(widget)
        self.advance_line_edit.setText("0 s")
        layout.addRow("<i>τ</i>", self.advance_line_edit)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        proxy.setWidget(widget)
        self.set_item(proxy)

    def set_advance(self, advance: Expression) -> None:
        self.advance_line_edit.setText(str(advance))

    def get_advance(self) -> Expression:
        return Expression(self.advance_line_edit.text())


class DelayBlock(FunctionalBlock):
    """Represents a block that shifts the input signal to future times."""

    def __init__(self, parent=None):
        super().__init__(
            number_input_connections=1, has_output_connection=True, parent=parent
        )

        proxy = QGraphicsProxyWidget()
        widget = QWidget()
        widget.setLayout(layout := QFormLayout(widget))
        label = QLabel("<i>y(t) = x(t - τ)</i>", widget)
        layout.addRow("Delay", label)
        self.delay_line_edit = QLineEdit(widget)
        self.delay_line_edit.setText("0 s")
        layout.addRow("<i>τ</i>", self.delay_line_edit)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        proxy.setWidget(widget)
        self.set_item(proxy)

    def set_delay(self, delay: Expression) -> None:
        self.delay_line_edit.setText(str(delay))

    def get_delay(self) -> Expression:
        return Expression(self.delay_line_edit.text())

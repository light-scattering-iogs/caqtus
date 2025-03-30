from caqtus_parsing import parse
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QToolButton,
    QWidget,
)

from caqtus.types.expression import Expression

from ..condetrol._icons import get_icon
from ._value_editor import ValueEditor


class ExpressionEditor(ValueEditor[Expression]):
    def __init__(self) -> None:
        self._line_edit = _ExpressionLineEdit()

    def set_value(self, value: Expression) -> None:
        self._line_edit.set_value(value)

    def read_value(self) -> Expression:
        return self._line_edit.read_value()

    def set_editable(self, editable: bool) -> None:
        self._line_edit.set_editable(editable)

    @property
    def widget(self) -> QWidget:
        return self._line_edit


class _ExpressionLineEdit(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._line_edit = QLineEdit(self)
        self._button = QToolButton(self)
        self._button.setIcon(get_icon("mdi6.alert", color="orange"))
        self._button.setVisible(False)
        self._button.setToolTipDuration(30_000)
        self._layout.addWidget(self._line_edit)
        self._layout.addWidget(self._button)
        self.setLayout(self._layout)
        self._line_edit.setPlaceholderText("Variable or math expression")
        self._line_edit.textEdited.connect(self._on_text_edited)

    def set_value(self, value: Expression) -> None:
        self._line_edit.setText(str(value))
        self._on_text_edited()

    def read_value(self) -> Expression:
        return Expression(self._line_edit.text())

    def set_editable(self, editable: bool) -> None:
        self._line_edit.setReadOnly(not editable)

    def _on_text_edited(self) -> None:
        text = self._line_edit.text()
        if not text:
            self._button.setToolTip("")
            self._button.setVisible(False)
            return
        try:
            parse(text)
        except ValueError as e:
            self._button.setToolTip(str(e))
            self._button.setVisible(True)
        else:
            self._button.setToolTip("")
            self._button.setVisible(False)

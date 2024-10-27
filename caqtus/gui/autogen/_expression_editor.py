from PySide6.QtWidgets import QLineEdit

from caqtus.types.expression import Expression
from ._value_editor import ValueEditor


class ExpressionEditor(ValueEditor[Expression]):
    def __init__(self) -> None:
        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText("Variable or math expression")

    def set_value(self, value: Expression) -> None:
        self._line_edit.setText(str(value))

    def read_value(self) -> Expression:
        return Expression(self._line_edit.text())

    def set_editable(self, editable: bool) -> None:
        self._line_edit.setReadOnly(not editable)

    def widget(self) -> QLineEdit:
        return self._line_edit

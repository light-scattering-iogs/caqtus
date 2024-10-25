from typing import Optional

from PySide6.QtWidgets import QLineEdit, QWidget

from ._value_editor import ValueEditor


class StringEditor(ValueEditor[str]):
    def __init__(self, value: str, parent: Optional[QWidget] = None) -> None:
        self.line_edit = QLineEdit(parent)
        self.line_edit.setText(value)

    def read_value(self) -> str:
        return self.line_edit.text()

    def set_editable(self, editable: bool) -> None:
        self.line_edit.setReadOnly(not editable)

    def widget(self) -> QWidget:
        return self.line_edit

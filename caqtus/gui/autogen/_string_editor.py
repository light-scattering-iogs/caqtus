from PySide6.QtWidgets import QLineEdit

from ._value_editor import ValueEditor


class StringEditor(ValueEditor[str]):
    """An editor to display a string.

    Args:
        placeholder: The text to display when the editor is empty.
    """

    def __init__(self, placeholder: str = "") -> None:
        self.line_edit = QLineEdit()

        if placeholder:
            self.line_edit.setPlaceholderText(placeholder)

    def set_value(self, value: str) -> None:
        self.line_edit.setText(value)

    def read_value(self) -> str:
        return self.line_edit.text()

    def set_editable(self, editable: bool) -> None:
        self.line_edit.setReadOnly(not editable)

    def widget(self) -> QLineEdit:
        return self.line_edit

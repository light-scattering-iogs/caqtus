from PySide6.QtWidgets import QLineEdit

from ._value_editor import ValueEditor


class StringEditor(ValueEditor[str]):
    """An editor to display a string.

    Args:
        value: The initial value to edit.
            Once initialized, the value can only be changed by the user through the
            widget.
        placeholder: The text to display when the editor is empty.
    """

    def __init__(self, value: str, placeholder: str = "") -> None:
        self.line_edit = QLineEdit()
        self.line_edit.setText(value)

        if placeholder:
            self.line_edit.setPlaceholderText(placeholder)

    def read_value(self) -> str:
        return self.line_edit.text()

    def set_editable(self, editable: bool) -> None:
        self.line_edit.setReadOnly(not editable)

    def widget(self) -> QLineEdit:
        return self.line_edit

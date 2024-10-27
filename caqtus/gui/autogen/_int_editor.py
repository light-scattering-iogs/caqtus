from PySide6.QtWidgets import QSpinBox

from ._value_editor import ValueEditor


class IntegerEditor(ValueEditor[int]):
    def __init__(
        self,
        value: int,
        *,
        min_value=0,
        max_value=999,
    ) -> None:
        self.spin_box = QSpinBox()
        self.spin_box.setRange(min_value, max_value)
        if not min_value <= value <= max_value:
            raise ValueError(
                f"Value {value} is outside the editor range [{min_value}, {max_value}]"
            )
        self.spin_box.setValue(value)

    def read_value(self) -> int:
        return self.spin_box.value()

    def set_editable(self, editable: bool) -> None:
        self.spin_box.setReadOnly(not editable)

    def widget(self) -> QSpinBox:
        return self.spin_box

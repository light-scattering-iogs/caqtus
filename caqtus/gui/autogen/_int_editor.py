from PySide6.QtWidgets import QSpinBox

from ._value_editor import ValueEditor


class IntegerEditor(ValueEditor[int]):
    """An editor to display an integer.

    Args:
        min_value: The lowest value (inclusive) that can be entered.
        max_value: The largest value (inclusive) that can be entered.
        prefix: A string to be displayed before the number.
        suffix: A string to be displayed after the number.
    """

    def __init__(
        self,
        min_value=0,
        max_value=999,
        prefix: str = "",
        suffix: str = "",
    ) -> None:
        self.spin_box = QSpinBox()
        self.spin_box.setRange(min_value, max_value)
        self._min_value = min_value
        self._max_value = max_value

        if prefix:
            self.spin_box.setPrefix(prefix)
        if suffix:
            self.spin_box.setSuffix(suffix)

    def set_value(self, value: int) -> None:
        if not self._min_value <= value <= self._max_value:
            raise ValueError(
                f"Value {value} is outside the editor range "
                f"[{self._min_value}, {self._max_value}]"
            )
        self.spin_box.setValue(value)

    def read_value(self) -> int:
        return self.spin_box.value()

    def set_editable(self, editable: bool) -> None:
        self.spin_box.setReadOnly(not editable)

    def widget(self) -> QSpinBox:
        return self.spin_box

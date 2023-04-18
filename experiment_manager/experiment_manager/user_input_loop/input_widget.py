from numbers import Real
from typing import NamedTuple, Optional

from PyQt6.QtWidgets import QDialog, QFormLayout, QSpinBox

from units import Unit
from variable_name import VariableName


class EvaluatedVariableRange(NamedTuple):
    minimum: Real
    maximum: Real
    initial_value: Real
    unit: Optional[Unit]


class UserInputDialog(QDialog):
    def __init__(self, title: str, variable_ranges: dict[VariableName, EvaluatedVariableRange]):
        super().__init__()
        self.setWindowTitle(title)

        layout = QFormLayout()
        for variable_name in variable_ranges:
            layout.addRow(str(variable_name), QSpinBox())
        self.setLayout(layout)

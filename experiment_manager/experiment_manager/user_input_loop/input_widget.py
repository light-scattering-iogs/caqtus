from numbers import Real
from typing import NamedTuple, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QWidget,
    QHBoxLayout,
    QSlider,
    QDoubleSpinBox,
)

from units import Unit, unit_registry
from variable_name import VariableName


class EvaluatedVariableRange(NamedTuple):
    minimum: Real
    maximum: Real
    initial_value: Real
    unit: Optional[Unit]


class UserInputDialog(QDialog):
    def __init__(
        self,
        title: str,
        variable_ranges: dict[VariableName, EvaluatedVariableRange],
    ):
        super().__init__()
        self.setWindowTitle(title)
        self._selector_widgets = {}

        layout = QFormLayout()
        for variable_name, variable_range in variable_ranges.items():
            widget = SelectorWidget(
                variable_range.minimum,
                variable_range.maximum,
                variable_range.initial_value,
                variable_range.unit,
            )
            layout.addRow(str(variable_name), widget)
            self._selector_widgets[variable_name] = widget
        self.setLayout(layout)

    def get_current_values(self) -> dict[VariableName, Real]:
        return {variable_name: widget.value for variable_name, widget in self._selector_widgets.items()}


class SelectorWidget(QWidget):

    def __init__(
        self, minimum: Real, maximum: Real, initial_value: Real, unit: Optional[Unit]
    ):
        super().__init__()
        self._minimum = minimum
        self._maximum = maximum
        layout = QHBoxLayout()
        self.setLayout(layout)

        self._spin_box = QDoubleSpinBox()
        self._spin_box.setRange(minimum, maximum)
        self._spin_box.setValue(initial_value)
        self._spin_box.valueChanged.connect(self._spin_box_changed)
        self._spin_box.setDecimals(3)
        if unit is not None:
            symbol = unit_registry.get_symbol(str(unit))
            self._spin_box.setSuffix(f" {symbol}")

        self._slider = QSlider()
        self._slider.setOrientation(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(self.to_slider(initial_value))
        self._slider.valueChanged.connect(self._slider_changed)

        layout.addWidget(self._slider)
        layout.addWidget(self._spin_box)

    def to_slider(self, value: Real):
        return int((value - self._minimum) / (self._maximum - self._minimum) * 1000)

    def from_slider(self, value: int):
        return self._minimum + (self._maximum - self._minimum) * value / 1000

    def _slider_changed(self, value: int):
        self._spin_box.setValue(self.from_slider(value))

    def _spin_box_changed(self, value: Real):
        self._slider.setValue(self.to_slider(value))

    @property
    def value(self) -> Real:
        return self._spin_box.value()

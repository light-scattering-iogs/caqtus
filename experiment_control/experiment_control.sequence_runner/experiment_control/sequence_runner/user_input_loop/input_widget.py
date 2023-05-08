from numbers import Real
from typing import NamedTuple, Optional

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QWidget,
    QHBoxLayout,
    QDoubleSpinBox,
    QDial,
)

from units import Unit, unit_registry, AnalogValue
from variable.name import DottedVariableName


class EvaluatedVariableRange(NamedTuple):
    minimum: AnalogValue
    maximum: AnalogValue
    initial_value: AnalogValue


class RawVariableRange(NamedTuple):
    minimum: Real
    maximum: Real
    initial_value: Real
    unit: Optional[Unit]


class UserInputDialog(QDialog):
    def __init__(
        self,
        title: str,
        variable_ranges: dict[DottedVariableName, RawVariableRange],
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
        layout.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

    def get_current_values(self) -> dict[DottedVariableName, Real]:
        return {
            variable_name: widget.value
            for variable_name, widget in self._selector_widgets.items()
        }


NUMBER_OF_DECIMALS = 3
STEP = 1 / 10**NUMBER_OF_DECIMALS


class SelectorWidget(QWidget):
    def __init__(
        self, minimum: Real, maximum: Real, initial_value: Real, unit: Optional[Unit]
    ):
        super().__init__()
        self._minimum = minimum
        self._maximum = maximum
        layout = QHBoxLayout()
        self.setLayout(layout)

        self.slider_range = int((self._maximum - self._minimum) / STEP)

        self._spin_box = QDoubleSpinBox()
        self._spin_box.setRange(minimum, maximum)
        self._spin_box.setValue(initial_value)
        self._spin_box.valueChanged.connect(self._spin_box_changed)
        self._spin_box.setDecimals(3)
        if unit is not None:
            symbol = unit_registry.get_symbol(str(unit))
            self._spin_box.setSuffix(f" {symbol}")

        self._slider = QDial()
        self._slider.setWrapping(False)
        self._slider.setSingleStep(1)
        self._slider.setNotchesVisible(True)
        self._slider.setNotchTarget(50)
        self._slider.setPageStep(100)
        self._slider.setRange(0, self.slider_range)
        self._slider.setValue(self.to_slider(initial_value))
        self._slider.valueChanged.connect(self._slider_changed)

        layout.addWidget(self._slider)
        layout.addWidget(self._spin_box)

    def to_slider(self, value: Real):
        return int(
            (value - self._minimum)
            / (self._maximum - self._minimum)
            * self.slider_range
        )

    def from_slider(self, value: int):
        return (
            self._minimum + (self._maximum - self._minimum) * value / self.slider_range
        )

    def _slider_changed(self, value: int):
        with QSignalBlocker(self._spin_box):
            self._spin_box.setValue(self.from_slider(value))

    def _spin_box_changed(self, value: Real):
        with QSignalBlocker(self._slider):
            self._slider.setValue(self.to_slider(value))

    @property
    def value(self) -> Real:
        return self._spin_box.value()

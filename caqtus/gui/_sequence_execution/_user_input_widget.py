"""This module defines the :class `UserInputWidget`.

This widget is used when a sequence execution requires user input to specify the value
of some parameters.
"""

import abc
from typing import assert_never

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSlider,
    QWidget,
)

from caqtus.gui.qtutil import QABCMeta
from caqtus.types.iteration._tunable_parameter_config import (
    AnalogRange,
    DigitalInput,
    InputSchema,
    InputType,
)
from caqtus.types.parameter import Parameter
from caqtus.types.units import Unit
from caqtus.types.variable_name import DottedVariableName


class UserInputWidget(QWidget):
    """A widget for collecting user input during sequence execution.

    Args:
        input_schema: A mapping from variable names to input types, defining the schema
            for user inputs.
            The widget will present a list of input fields to the user corresponding to
            the value contained in this mapping.

        parent: The parent widget of this widget. Defaults to None.


    Example:
        >>> from caqtus.gui._sequence_execution import (
            UserInputWidget,
            AnalogRange,
            DigitalInput,
        )
        >>> from caqtus.types.variable_name import DottedVariableName
        >>> from caqtus.types.units import Unit
        >>> input_schema = {
            DottedVariableName("example.variable"): AnalogRange(0.0, 10.0, Unit("V")),
            DottedVariableName("example.digital_input"): DigitalInputConfig(),
        }
        >>> widget = UserInputWidget(input_schema)
        >>> assert widget.get_current_values() == {
            DottedVariableName("example.variable"): Quantity(5.0, Unit("V")),
            DottedVariableName("example.digital_input"): True,
        }
    """

    def __init__(self, input_schema: InputSchema, parent: QWidget | None = None):
        """Initialize the UserInputWidget.

        Args:
            parent: The parent widget of this widget. Defaults to None.
        """

        super().__init__(parent)
        self._input_schema = dict(input_schema)
        self._input_widgets = {
            variable_name: _create_input_widget(input_type)
            for variable_name, input_type in self._input_schema.items()
        }
        layout = QGridLayout()
        for row, (variable_name, input_widget) in enumerate(
            self._input_widgets.items()
        ):
            layout.addWidget(QLabel(str(variable_name)), row, 0)
            layout.addWidget(input_widget, row, 1)
        self.setLayout(layout)

    def get_current_values(self) -> dict[DottedVariableName, Parameter]:
        """Get the current values from all input widgets.

        Returns:
            A dictionary mapping variable names to their current values.
        """

        return {
            variable_name: input_widget.get_value()
            for variable_name, input_widget in self._input_widgets.items()
        }


class InputWidget(QWidget, metaclass=QABCMeta):
    @abc.abstractmethod
    def get_value(self) -> Parameter:
        """Get the current value from the input widget."""
        raise NotImplementedError


class AnalogInputWidget(InputWidget):
    def __init__(self, minimum: float, maximum: float, unit: Unit):
        super().__init__()
        layout = QHBoxLayout()
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        layout.addWidget(self._slider)
        self.setLayout(layout)
        self._minimum = minimum
        self._maximum = maximum
        self._unit = unit
        self._spinbox = QDoubleSpinBox()
        self._spinbox.setRange(minimum, maximum)
        self._spinbox.setSingleStep((maximum - minimum) / 100)
        self._spinbox.setSuffix(f" {unit:~}")
        self._slider.valueChanged.connect(self._on_slider_value_changed)
        self._spinbox.valueChanged.connect(self._on_spinbox_value_changed)
        layout.addWidget(self._spinbox)
        self._slider.setValue(50)

    def _on_slider_value_changed(self, value: int):
        scaled_value = self._minimum + (self._maximum - self._minimum) * value / 100
        with QSignalBlocker(self._spinbox):
            self._spinbox.setValue(scaled_value)

    def _on_spinbox_value_changed(self):
        value = self._spinbox.value()
        scaled_value = (value - self._minimum) / (self._maximum - self._minimum) * 100
        with QSignalBlocker(self._slider):
            self._slider.setValue(int(scaled_value))

    def get_value(self) -> Parameter:
        return self._spinbox.value() * self._unit


class DigitalInputWidget(InputWidget):
    def __init__(self):
        super().__init__()
        self._button_group = QButtonGroup()
        self._enabled_button = QRadioButton("Enabled")
        self._disabled_button = QRadioButton("Disabled")
        self._enabled_button.setChecked(True)
        self._button_group.addButton(self._enabled_button)
        self._button_group.addButton(self._disabled_button)
        layout = QHBoxLayout()
        layout.addWidget(self._enabled_button)
        layout.addWidget(self._disabled_button)
        self.setLayout(layout)

    def get_value(self) -> Parameter:
        return self._enabled_button.isChecked()


def _create_input_widget(input_type: InputType) -> InputWidget:
    match input_type:
        case AnalogRange(minimum, maximum, unit):
            return AnalogInputWidget(minimum, maximum, unit)
        case DigitalInput():
            return DigitalInputWidget()
        case _:
            assert_never(input_type)

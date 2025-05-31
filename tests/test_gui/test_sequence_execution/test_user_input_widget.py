from pytestqt.qtbot import QtBot

from caqtus.gui._sequence_execution import AnalogRange, DigitalInput, UserInputWidget
from caqtus.types.units import Quantity, Unit
from caqtus.types.variable_name import DottedVariableName


def test_user_input_widget(qtbot: QtBot):
    input_schema = {
        DottedVariableName("example.variable"): AnalogRange(0.0, 10.0, Unit("V")),
        DottedVariableName("example.digital_input"): DigitalInput(),
    }
    widget = UserInputWidget(input_schema)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.stop()
    assert widget.get_current_values() == {
        DottedVariableName("example.variable"): Quantity(5.0, Unit("V")),
        DottedVariableName("example.digital_input"): True,
    }

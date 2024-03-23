import sys

from PySide6.QtWidgets import (
    QApplication,
)

from condetrol.parameter_tables_editor import ParameterNamespaceEditor
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
import qdarkstyle

app = QApplication(sys.argv)
app.setStyleSheet(qdarkstyle.load_stylesheet())
editor = ParameterNamespaceEditor()
editor.set_read_only(False)


parameters = {
    DottedVariableName("mot_loading"): {
        DottedVariableName("detuning"): Expression("-3 MHz"),
        DottedVariableName("duration"): Expression("100 ms"),
        DottedVariableName("red_frequncy"): Expression("1 MHz"),
        DottedVariableName("red_power"): Expression("0 dB"),
    },
    DottedVariableName("b"): Expression("2"),
    DottedVariableName("c"): Expression("3"),
}

editor.show()
editor.set_parameters(parameters)
app.exec_()

assert editor.get_parameters() == parameters

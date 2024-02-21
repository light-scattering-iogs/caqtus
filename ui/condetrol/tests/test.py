import sys

from PySide6.QtWidgets import QApplication, QColumnView, QLabel

from condetrol.parameter_tables_editor import ParameterNamespaceModel
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName


class View(QColumnView):
    def setPreviewWidget(self, widget):
        pass


app = QApplication(sys.argv)
view = View()
model = ParameterNamespaceModel(view)
# view.setColumnWidths([0])
view.setModel(model)
model.set_namespace(
    {
        DottedVariableName("mot_loading"): {
            DottedVariableName("detuning"): Expression("-3 MHz"),
            DottedVariableName("duration"): Expression("100 ms"),
        },
        DottedVariableName("b"): Expression("2"),
        DottedVariableName("c"): Expression("3"),
    }
)
view.show()
sys.exit(app.exec_())

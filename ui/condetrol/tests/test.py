import sys

from PySide6.QtWidgets import (
    QApplication,
    QColumnView,
    QLabel,
    QListView,
    QWidget,
    QSizePolicy,
)

from condetrol.parameter_tables_editor import ParameterNamespaceModel
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName


class View(QColumnView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # stupid fix to make the preview widget not show
        # see: https://bugreports.qt.io/browse/QTBUG-1826

        self.w = QWidget()
        self.w.setMaximumSize(0, 0)
        self.w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setPreviewWidget(self.w)
        self.updatePreviewWidget.connect(self.on_update_preview_widget)

    def on_update_preview_widget(self, index):
        self.w.parentWidget().parentWidget().setMinimumWidth(0)
        self.w.parentWidget().parentWidget().setMaximumWidth(0)


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

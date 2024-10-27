from typing import Optional

from PySide6.QtGui import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QComboBox,
    QStackedWidget,
    QLineEdit,
    QLabel,
    QSizePolicy,
)

from ._value_editor import ValueEditor
from ...device.output_transform import EvaluableOutput
from ...types.expression import Expression


class OutputTransformEditor(ValueEditor[EvaluableOutput]):
    def __init__(
        self, value: EvaluableOutput, parent: Optional[QWidget] = None
    ) -> None:
        self._widget = QWidget(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self._widget.setLayout(layout)
        self._combo_box = QComboBox()
        self._combo_box.addItem("Expression")
        self._combo_box.addItem("Tree")
        layout.addWidget(self._combo_box)
        layout.setAlignment(self._combo_box, Qt.AlignmentFlag.AlignTop)

        self._expression = QLineEdit()
        self._expression.setPlaceholderText("A variable or a mathematical expression")

        self._tree = QLabel("Not implemented")
        self._stacked_widget = QStackedWidget()
        self._stacked_widget.addWidget(self._expression)
        self._stacked_widget.addWidget(self._tree)
        self._combo_box.currentIndexChanged.connect(
            self._stacked_widget.setCurrentIndex
        )

        layout.addWidget(self._stacked_widget)
        self._stacked_widget.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        )
        self.set_value(value)

    def set_value(self, value: EvaluableOutput) -> None:
        if isinstance(value, Expression):
            self._combo_box.setCurrentIndex(0)
            self._expression.setText(str(value))
        else:
            self._combo_box.setCurrentIndex(1)

    def widget(self) -> QWidget:
        return self._widget

    def set_editable(self, editable: bool) -> None:
        self._combo_box.setEnabled(editable)

    def read_value(self) -> EvaluableOutput:
        if self._combo_box.currentIndex() == 0:
            return Expression(self._expression.text())
        else:
            raise NotImplementedError("Tree output transform not implemented")

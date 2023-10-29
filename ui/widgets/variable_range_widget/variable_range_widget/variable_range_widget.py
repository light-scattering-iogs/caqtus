from typing import Optional

from PyQt6.QtCore import QModelIndex
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from sequence.configuration import VariableRange
from variable.name import DottedVariableName
from .variable_range_model import VariableRangeModel
from .variable_range_table import VariableRangeTable


class VariableRangeWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._model = VariableRangeModel({})
        self._table = VariableRangeTable()
        self._table.setModel(self._model)

        buttons_layout = QHBoxLayout()
        add_button = QPushButton("+")
        add_button.clicked.connect(self._add_variable)
        add_button.setFixedWidth(add_button.sizeHint().height())
        buttons_layout.addWidget(add_button)
        remove_button = QPushButton("-")
        remove_button.setFixedWidth(remove_button.sizeHint().height())
        remove_button.clicked.connect(self._remove_variable)
        buttons_layout.addWidget(remove_button)
        buttons_layout.addStretch(1)

        layout = QVBoxLayout()
        layout.addWidget(self._table)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    @property
    def variable_ranges(self) -> dict[DottedVariableName, VariableRange]:
        return self._model.variable_ranges

    @variable_ranges.setter
    def variable_ranges(self, variable_ranges: dict[DottedVariableName, VariableRange]):
        self._model.variable_ranges = variable_ranges

    def _add_variable(self):
        self._model.insertRow(self._model.rowCount(), QModelIndex())

    def _remove_variable(self):
        rows = [index.row() for index in self._table.selectedIndexes()]
        rows.sort(reverse=True)
        for row in rows:
            self._model.removeRow(row, QModelIndex())

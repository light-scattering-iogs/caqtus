from PyQt6.QtCore import QAbstractItemModel
from PyQt6.QtWidgets import QTableView

from sequence.configuration import VariableRange
from variable.name import DottedVariableName
from variable_range_widget import VariableRangeModel


class VariableRangeTable(QTableView):
    def setModel(self, model: QAbstractItemModel) -> None:
        if not isinstance(model, VariableRangeModel):
            raise TypeError(f"Expected a VariableRangeModel, got {model}")
        super().setModel(model)

    @property
    def variable_ranges(self) -> dict[DottedVariableName, VariableRange]:
        model = self.model()
        if not isinstance(model, VariableRangeModel):
            raise TypeError(f"Expected a VariableRangeModel, got {model}")
        return model.variable_ranges

    @variable_ranges.setter
    def variable_ranges(self, variable_ranges: dict[DottedVariableName, VariableRange]):
        model = self.model()
        if not isinstance(model, VariableRangeModel):
            raise TypeError(f"Expected a VariableRangeModel, got {model}")
        model.variable_ranges = variable_ranges

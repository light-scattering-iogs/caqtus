import logging

from PyQt6.QtCore import QModelIndex, Qt, QAbstractTableModel

from expression import Expression
from rename_dict_key import rename_dict_key
from sequence.configuration import VariableRange
from variable.name import DottedVariableName

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class VariableRangeModel(QAbstractTableModel):
    """Table model to edit the range of some variables.

    This model is used when we need to configure an allowed space for some variables, along with an initial value in
    this space.
    Each row of the table represents a variable. The columns are:
    - Variable name: name of the variable
    - From: minimum bound of the range
    - To: maximum bound of the range
    - Initial value: initial value of the variable in the range
    """

    def __init__(self, variable_ranges: dict[DottedVariableName, VariableRange]):
        super().__init__()
        self.variable_ranges = variable_ranges

    @property
    def variable_ranges(self):
        return self._variables.copy()

    @variable_ranges.setter
    def variable_ranges(self, variable_ranges: dict[DottedVariableName, VariableRange]):
        self.beginResetModel()
        self._variables = variable_ranges.copy()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self._variables)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 4

    def data(self, index: QModelIndex, role: int = ...):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            variable_name = list(self._variables.keys())[index.row()]
            if index.column() == 0:
                return str(variable_name)
            elif index.column() == 1:
                return self._variables[variable_name].first_bound.body
            elif index.column() == 2:
                return self._variables[variable_name].second_bound.body
            elif index.column() == 3:
                return self._variables[variable_name].initial_value.body
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            if section == 0:
                return "Variable"
            elif section == 1:
                return "From"
            elif section == 2:
                return "To"
            elif section == 3:
                return "Initial value"
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index: QModelIndex, value, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            variable_name = list(self._variables.keys())[index.row()]
            if index.column() == 0:
                self._variables = rename_dict_key(self._variables, variable_name, value)
            elif index.column() == 1:
                self._variables[variable_name].first_bound = Expression(value)
            elif index.column() == 2:
                self._variables[variable_name].second_bound = Expression(value)
            elif index.column() == 3:
                self._variables[variable_name].initial_value = Expression(value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def insertRow(self, row: int, parent: QModelIndex) -> bool:
        self.beginInsertRows(parent, row, row)
        variable_name = self._get_first_available_variable_name("variable")
        self._variables[variable_name] = VariableRange(
            first_bound=Expression("..."),
            second_bound=Expression("..."),
            initial_value=Expression("..."),
        )
        self.endInsertRows()
        return True

    def _get_first_available_variable_name(
        self, variable_name: str
    ) -> DottedVariableName:
        """Return the first available variable name starting from the given one."""

        variable_name: DottedVariableName = DottedVariableName(variable_name)
        if variable_name not in self._variables:
            return variable_name
        i = 1
        while True:
            new_variable_name = DottedVariableName(f"{variable_name}_{i}")
            if new_variable_name not in self._variables:
                return new_variable_name
            i += 1

    def removeRow(self, row: int, parent: QModelIndex) -> bool:
        variable_name = list(self._variables.keys())[row]
        self.beginRemoveRows(parent, row, row)
        self._variables.pop(variable_name)
        self.endRemoveRows()
        return True

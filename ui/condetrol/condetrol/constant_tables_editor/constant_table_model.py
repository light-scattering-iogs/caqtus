import copy
from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QObject, Qt, QModelIndex

from core.session import ConstantTable
from core.session.sequence.iteration_configuration import VariableDeclaration
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName


class ConstantTableModel(QAbstractListModel):
    def __init__(self, parent=Optional[QObject]):
        super().__init__(parent)
        self.table = []

    def rowCount(self, parent=None, *args, **kwargs):
        return len(self.table)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self.table[index.row()]

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole:
            for attribute, new_value in value.items():
                setattr(self.table[index.row()], attribute, new_value)
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )
        return flags

    def set_table(self, table: ConstantTable):
        self.beginResetModel()
        self.table = copy.deepcopy(table)
        self.endResetModel()

    def get_table(self) -> ConstantTable:
        return copy.deepcopy(self.table)

    def insertRow(self, row, parent=QModelIndex()):
        self.beginInsertRows(parent, row, row)
        declaration = VariableDeclaration(
            variable=DottedVariableName("new_variable"), value=Expression("...")
        )
        self.table.insert(row, declaration)
        self.endInsertRows()

from collections.abc import Mapping
from typing import Optional, assert_never

from PySide6.QtCore import (
    QObject,
    QModelIndex,
    Qt,
    QAbstractItemModel,
)
from PySide6.QtWidgets import QWidget, QListView

from core.session import ConstantTable
from .parameter_tables_editor_ui import Ui_ParameterTablesEditor
from ..icons import get_icon


class ParameterTablesEditor(QWidget, Ui_ParameterTablesEditor):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()
        self.set_read_only(False)
        self.view = self.columnView
        self._model = ParameterTablesModel(self)
        self.view.setModel(self._model)

    def set_parameter_tables(self, tables: Mapping[str, ConstantTable]) -> None:
        self._model.set_parameter_tables(tables)

    def setup_ui(self):
        self.setupUi(self)
        color = self.palette().buttonText().color()
        self.add_button.setIcon(get_icon("plus", color))
        self.delete_button.setIcon(get_icon("minus", color))

    def set_read_only(self, read_only: bool) -> None:
        if read_only:
            self.on_set_to_read_only()
        else:
            self.on_set_to_editable()

    def on_set_to_read_only(self) -> None:
        self.add_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def on_set_to_editable(self) -> None:
        self.add_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def set_tables(self, tables: Mapping[str, ConstantTable]):
        # The palette is not set yet in the __init__, so we need to update the icons
        # here, now that it is set to have the right color.
        color = self.palette().buttonText().color()
        self.add_button.setIcon(get_icon("plus", color))
        self.delete_button.setIcon(get_icon("minus", color))


class ParameterTablesModel(QAbstractItemModel):
    def __init__(self, parent: Optional[QObject]):
        super().__init__(parent)

        self.tables: list[tuple[str, ConstantTable]] = []

    def set_parameter_tables(self, tables: Mapping[str, ConstantTable]) -> None:
        self.beginResetModel()
        self.tables = [(name, table) for name, table in tables.items()]
        self.endResetModel()
        print(self.tables)

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()):
        if self.hasIndex(row, column, parent):
            if not parent.isValid():
                return self.createIndex(row, column, (row,))
            else:
                table_index = parent.internalPointer()[0]
                return self.createIndex(row, column, (table_index, row))
        else:
            return QModelIndex()

    def parent(self, child: QModelIndex = QModelIndex()) -> QModelIndex:
        if child.isValid():
            internal_pointer = child.internalPointer()
            match internal_pointer:
                case (table_index,):
                    return QModelIndex()
                case (table_index, param_index):
                    return self.createIndex(table_index, child.column(), (table_index,))
                case _:
                    assert_never(internal_pointer)
        else:
            return QModelIndex()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self.tables)
        internal_pointer = parent.internalPointer()
        match internal_pointer:
            case (table_index,):
                return len(self.get_table(table_index))
            case (table_index, param_index):
                return 0
            case _:
                assert_never(internal_pointer)

    def get_table(self, index: int) -> ConstantTable:
        return self.tables[index][1]

    def get_table_name(self, index: int) -> str:
        return self.tables[index][0]

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            internal_pointer = index.internalPointer()
            print(internal_pointer, flush=True)
            match internal_pointer:
                case (table_index,):
                    return self.get_table_name(table_index)
                case (table_index, param_index):
                    return str(self.get_table(table_index)[param_index])
        return None

from collections.abc import Mapping
from typing import Optional, assert_never

from PySide6.QtCore import (
    QObject,
    QModelIndex,
    Qt,
    QAbstractItemModel,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QWidget

from core.session import ConstantTable, ParameterNamespace, is_parameter_namespace
from core.types.expression import Expression
from core.types.variable_name import DottedVariableName
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


class ParameterNamespaceModel(QStandardItemModel):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    def set_namespace(self, namespace: ParameterNamespace) -> None:
        root = self.invisibleRootItem()
        root.removeRows(0, root.rowCount())
        for name, value in namespace.items():
            item = self._create_item(name, value)
            root.appendRow(item)

    def get_namespace(self) -> ParameterNamespace:
        namespace = {}
        root = self.invisibleRootItem()
        for row in range(root.rowCount()):
            item = root.child(row)
            name = DottedVariableName(item.data(Qt.ItemDataRole.DisplayRole))
            value = item.data(Qt.ItemDataRole.UserRole)
            if value is None:
                value = self.get_namespace_from_item(item)
            namespace[name] = value
        return namespace

    def _create_item(
        self, name: DottedVariableName, value: ParameterNamespace | Expression
    ) -> QStandardItem:
        item = QStandardItem()
        if isinstance(value, Expression):
            item.setData(f"{name} = {value}", Qt.ItemDataRole.DisplayRole)
            item.setData(value, Qt.ItemDataRole.UserRole)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemNeverHasChildren
            )
        elif is_parameter_namespace(value):
            item.setData(str(name), Qt.ItemDataRole.DisplayRole)
            item.setData(value, Qt.ItemDataRole.UserRole)
            for sub_name, sub_value in value.items():
                sub_item = self._create_item(sub_name, sub_value)
                item.appendRow(sub_item)
            item.setData(None, Qt.ItemDataRole.UserRole)
        else:
            raise ValueError(f"Invalid value {value}")
        return item


class ParameterTablesModel(QAbstractItemModel):
    def __init__(self, parent: Optional[QObject]):
        super().__init__(parent)

        self.tables: list[tuple[str, ConstantTable]] = []

    def set_parameter_tables(self, tables: Mapping[str, ConstantTable]) -> None:
        self.beginResetModel()
        self.tables = [(name, table) for name, table in tables.items()]
        self.endResetModel()

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

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QListView, QMenu

from core.session import ConstantTable
from .constant_table_model import ConstantTableModel
from ..sequence_iteration_editors.steps_iteration_editor.delegate import StepDelegate


class ConstantTableEditor(QListView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = ConstantTableModel(self)
        self.setModel(self.model)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setItemDelegate(StepDelegate(self))

    def set_table(self, table: ConstantTable):
        self.model.set_table(table)

    def get_table(self) -> ConstantTable:
        return self.model.get_table()

    def show_context_menu(self, position):
        index = self.indexAt(position)
        menu = QMenu(self)
        if not index.isValid():
            add_action = QAction("Add")
            add_action.triggered.connect(
                lambda: self.model.insertRow(self.model.rowCount())
            )
            menu.addAction(add_action)
        else:
            add_above_action = QAction("Insert above")
            add_above_action.triggered.connect(
                lambda: self.model.insertRow(index.row())
            )
            menu.addAction(add_above_action)
        menu.exec(self.mapToGlobal(position))

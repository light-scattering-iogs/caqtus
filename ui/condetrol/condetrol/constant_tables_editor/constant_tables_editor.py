from collections.abc import Mapping, Iterable
from typing import Optional

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QDialog

from core.session import ConstantTable
from .add_constant_table_ui import Ui_AddTableDialog
from .constant_table_editor import ConstantTableEditor
from .constant_tables_editor_ui import Ui_ConstantTablesEditor
from ..save_geometry_dialog import SaveGeometryDialog


class ConstantTablesEditor(SaveGeometryDialog, Ui_ConstantTablesEditor):
    def __init__(
        self,
        constant_tables: Mapping[str, ConstantTable],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.tables = dict(constant_tables)

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        self.setupUi(self)
        self.tab_widget.clear()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.tab_widget.removeTab)
        self.tab_widget.setMovable(True)
        for table_name, table in self.tables.items():
            table_editor = ConstantTableEditor()
            self.tab_widget.addTab(table_editor, table_name)
            table_editor.set_table(table)

    def setup_connections(self):
        # noinspection PyUnresolvedReferences
        self.add_button.clicked.connect(self.add_table)

    def add_table(self):
        validator = NewNameValidator(
            self.tab_widget.tabText(i) for i in range(self.tab_widget.count())
        )
        add_table_dialog = AddTableDialog(
            validator,
        )
        name = add_table_dialog.exec()
        if name is not None:
            table_editor = ConstantTableEditor()
            self.tab_widget.addTab(table_editor, name)

    def exec(self):
        result = super().exec()
        if result == QDialog.DialogCode.Accepted:
            tables = {}
            for i in range(self.tab_widget.count()):
                table_editor = self.tab_widget.widget(i)
                table = table_editor.get_table()
                tables[self.tab_widget.tabText(i)] = table
            self.tables = tables
        return result


class AddTableDialog(QDialog, Ui_AddTableDialog):
    def __init__(self, validator: QValidator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.table_name_line_edit.setValidator(validator)

    def exec(self) -> Optional[str]:
        result = super().exec()
        if result == QDialog.DialogCode.Accepted:
            if not self.table_name_line_edit.hasAcceptableInput():
                return None
            table_name = self.table_name_line_edit.text()
            return table_name
        return None


class NewNameValidator(QValidator):
    def __init__(self, already_used_names: Iterable[str]):
        super().__init__()
        self.already_used_names = set(already_used_names)

    def validate(self, a0, a1):
        if a0 in self.already_used_names or a0 == "":
            return QValidator.State.Intermediate, a0, a1
        else:
            return QValidator.State.Acceptable, a0, a1

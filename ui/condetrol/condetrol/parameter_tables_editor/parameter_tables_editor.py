from typing import Optional

from PySide6.QtWidgets import QWidget
from .parameter_tables_editor_ui import Ui_ParameterTablesEditor


class ParameterTablesEditor(QWidget, Ui_ParameterTablesEditor):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)

from collections.abc import Mapping
from typing import Optional

from PySide6.QtWidgets import QWidget

from core.session import ConstantTable
from .parameter_tables_editor_ui import Ui_ParameterTablesEditor
from ..icons import get_icon


class ParameterTablesEditor(QWidget, Ui_ParameterTablesEditor):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setupUi(self)
        color = self.palette().buttonText().color()
        self.add_button.setIcon(get_icon("plus", color))
        self.delete_button.setIcon(get_icon("minus", color))

    def set_tables(self, tables: Mapping[str, ConstantTable]):
        # The palette is not set yet in the __init__, so we need to update the icons
        # here, now that it is set to have the right color.
        color = self.palette().buttonText().color()
        self.add_button.setIcon(get_icon("plus", color))
        self.delete_button.setIcon(get_icon("minus", color))

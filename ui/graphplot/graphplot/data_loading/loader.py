from typing import Optional

from PySide6.QtWidgets import QWidget

from .loader_ui import Ui_Form
class DataLoader(QWidget, Ui_Form):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
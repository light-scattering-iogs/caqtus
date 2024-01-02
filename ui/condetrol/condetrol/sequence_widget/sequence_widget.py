from PyQt6.QtWidgets import QWidget

from .sequence_widget_ui import Ui_SequenceWidget


class SequenceWidget(QWidget, Ui_SequenceWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

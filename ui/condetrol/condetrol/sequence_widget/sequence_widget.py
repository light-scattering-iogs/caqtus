from PyQt6.QtWidgets import QWidget
from core.session.sequence import State

from .sequence_widget_ui import Ui_SequenceWidget


class SequenceWidget(QWidget, Ui_SequenceWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.apply_state(State.DRAFT)

    def apply_state(self, state: State):
        if state == State.DRAFT:
            self.start_button.setEnabled(True)
        else:
            self.start_button.setEnabled(False)
        if state in {State.RUNNING}:
            self.interrupt_button.setEnabled(True)
        else:
            self.interrupt_button.setEnabled(False)
        if state in {State.FINISHED, State.INTERRUPTED, State.CRASHED}:
            self.clear_button.setEnabled(True)
        else:
            self.clear_button.setEnabled(False)

from typing import Optional

from PyQt6.QtWidgets import QWidget

from core.session import ExperimentSessionMaker, PureSequencePath, BoundSequencePath
from core.session.sequence import State, Sequence

from .sequence_widget_ui import Ui_SequenceWidget
from ..sequence_iteration_editors import create_default_editor


class SequenceWidget(QWidget, Ui_SequenceWidget):
    def __init__(
        self,
        sequence: PureSequencePath,
        session_maker: ExperimentSessionMaker,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.session_maker = session_maker
        self.sequence_path = sequence
        self.apply_state(State.DRAFT)

        with self.session_maker() as session:
            iteration_config = session.sequence_collection.get_iteration_configuration(
                Sequence(BoundSequencePath(self.sequence_path, session))
            )
        self.iteration_editor = create_default_editor(iteration_config)
        self.iteration_editor.iteration_changed.connect(
            self.on_sequence_iteration_changed
        )
        self.tabWidget.addTab(self.iteration_editor, "Iteration")

    def on_sequence_iteration_changed(self):
        iterations = self.iteration_editor.get_iteration()
        with self.session_maker() as session:
            session.sequence_collection.set_iteration_configuration(
                Sequence(BoundSequencePath(self.sequence_path, session)), iterations
            )

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

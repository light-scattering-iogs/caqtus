from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow

from experiment.session import ExperimentSessionMaker
from sequence.runtime import Sequence
from visual.viewer.sequence_viewer import SequenceViewer


class SequenceViewerWindow(QMainWindow):
    def __init__(self, session_maker: ExperimentSessionMaker):
        super().__init__()
        self._session_maker = session_maker

        sequence_viewer = SequenceViewer(
            Sequence("2023.03_March.17.test_3"), session_maker
        )

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, sequence_viewer)

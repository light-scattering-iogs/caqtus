import logging
import sys

import qdarkstyle
from PyQt6.QtWidgets import QApplication

from experiment.session import get_standard_experiment_session_maker
from sequence_viewer_window import SequenceViewerWindow


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


if __name__ == "__main__":
    sys.excepthook = except_hook

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    session_maker = get_standard_experiment_session_maker()
    sequence_viewer = SequenceViewerWindow(session_maker)
    sequence_viewer.show()
    app.exec()

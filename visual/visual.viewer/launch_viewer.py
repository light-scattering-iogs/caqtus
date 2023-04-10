import logging
import sys

import qdarkstyle
from PyQt6.QtWidgets import QApplication

from visual.viewer import SequenceViewerWindow


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
    sequence_viewer = SequenceViewerWindow()
    sequence_viewer.show()
    app.exec()

import logging
import sys

import qdarkstyle
from PyQt5.QtWidgets import QApplication

from experiment_viewer import ExperimentViewer


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


logging.basicConfig()
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    experiment_viewer = ExperimentViewer()
    experiment_viewer.show()
    try:
        app.exec()
    except Exception:
        logger.error("An exception occurred.", exc_info=True)

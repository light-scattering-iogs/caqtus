"""Starts an experiment manager in a different process and then creates and runs the
experiment viewer/sequences editor in the current process"""

import logging
import sys
from multiprocessing.managers import BaseManager

import qdarkstyle
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import QApplication

from experiment_manager import ExperimentManager
from experiment_viewer import ExperimentViewer


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentProcessManager(BaseManager):
    pass


ExperimentProcessManager.register("ExperimentManager", ExperimentManager)

if __name__ == "__main__":
    m = ExperimentProcessManager(address=("localhost", 60000), authkey=b"Deardear")
    m.start()
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    id = QFontDatabase.addApplicationFont(":/fonts/jetbrains-mono")
    if id < 0:
        logger.error("Could not load font jetbrains-mono")
    else:
        families = QFontDatabase.applicationFontFamilies(id)
    experiment_viewer = ExperimentViewer()
    experiment_viewer.show()
    try:
        app.exec()
    except Exception:
        logger.error("An exception occurred.", exc_info=True)
    m.shutdown()

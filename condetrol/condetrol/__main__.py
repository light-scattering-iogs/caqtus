"""Starts an experiment manager in a different process and then creates and runs the
experiment viewer/sequences editor in the current process"""

import logging
import os
import sys
from multiprocessing.managers import BaseManager

import qdarkstyle
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from experiment_manager import ExperimentManager, get_logs_queue
from experiment_viewer import ExperimentViewer


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentProcessManager(BaseManager):
    pass


ExperimentProcessManager.register("ExperimentManager", ExperimentManager)
ExperimentProcessManager.register("get_logs_queue", get_logs_queue)

DATABASE_URL = "postgresql+psycopg2://caqtus:Deardear@192.168.137.4/test_database"

if __name__ == "__main__":
    os.environ["QT_QUICK_CONTROLS_CONF"] = (
        "C:\\Users\\Damien"
        " Bloch\\Desktop\\caqtus_repo\\condetrol\\qtquickcontrols2.conf"
    )
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
    experiment_viewer = ExperimentViewer(DATABASE_URL)
    experiment_viewer.show()
    try:
        app.exec()
    except Exception:
        logger.error("An exception occurred.", exc_info=True)
    m.shutdown()

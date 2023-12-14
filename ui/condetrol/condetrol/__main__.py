"""Starts an experiment manager in a different process and then creates and runs the
experiment viewer/sequences editor in the current process"""

import logging
import sys
from pathlib import Path

import qdarkstyle
from PyQt6 import QtCore
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from condetrol.experiment_viewer import ExperimentViewer
from core.session import get_standard_experiment_session_maker


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
    fonts_path = Path(__file__).parent / "resources" / "fonts"
    QtCore.QDir.addSearchPath("fonts", str(fonts_path))
    icons_path = Path(__file__).parent.parent / "resources" / "icons"
    QtCore.QDir.addSearchPath("icons", str(icons_path))
    id = QFontDatabase.addApplicationFont("fonts:jetbrains-mono")
    if id < 0:
        logger.error("Could not load font jetbrains-mono")
    else:
        families = QFontDatabase.applicationFontFamilies(id)
    session_maker = get_standard_experiment_session_maker()
    with ExperimentViewer(session_maker) as experiment_viewer:
        experiment_viewer.show()
        try:
            app.exec()
        except Exception:
            logger.error("An exception occurred.", exc_info=True)

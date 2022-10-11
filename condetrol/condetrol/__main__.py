import logging
import sys

import qdarkstyle
import yaml
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import QApplication

from experiment_viewer import ExperimentViewer
from sequence import SequenceConfig, SequenceSteps, VariableDeclaration


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

s = SequenceConfig(program=SequenceSteps(children=[VariableDeclaration("a", "1")]))
# s = SequenceStats(state=SequenceState.DRAFT)

print(yaml.safe_dump(s, sort_keys=False))

if __name__ == "__main__":
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

import logging
import sys

import qdarkstyle
from PyQt6.QtWidgets import QApplication

from experiment.session import get_standard_experiment_session_maker
from viewer.single_shot_viewers import (
    SingleShotWidget,
)

logging.basicConfig(level=logging.INFO)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == "__main__":
    sys.excepthook = except_hook

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    widget = SingleShotWidget(
        experiment_session_maker=get_standard_experiment_session_maker(),
    )
    widget.show()

    app.exec()

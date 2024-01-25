import logging
import sys

import qdarktheme
from PyQt6.QtWidgets import QApplication

from core.session import get_standard_experiment_session_maker
from shotviewer.main_window import ShotViewerMainWindow
from shotviewer.single_shot_viewers.image_view import image_view_manager

logging.basicConfig(level=logging.INFO)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == "__main__":
    sys.excepthook = except_hook

    app = QApplication(sys.argv)
    qdarktheme.setup_theme(theme="dark")

    app.setStyle("Fusion")

    with ShotViewerMainWindow(
        experiment_session_maker=get_standard_experiment_session_maker(),
        view_managers={"Image": image_view_manager},
    ) as window:
        window.show()
        app.exec()

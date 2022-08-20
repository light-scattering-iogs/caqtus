import logging

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QMainWindow
from qtpy import QtGui

from .config_editor import ConfigEditor
from .experiment_viewer_ui import Ui_MainWindow

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentViewer(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui_settings = QSettings("Caqtus", "ExperimentControl")

        self.setupUi(self)
        self.restoreState(self.ui_settings.value(f"{__name__}/state", self.saveState()))
        self.restoreGeometry(
            self.ui_settings.value(f"{__name__}/geometry", self.saveGeometry())
        )

        self.action_edit_config.triggered.connect(self.edit_config)

    @staticmethod
    def edit_config():
        editor = ConfigEditor()
        editor.exec()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        state = self.saveState()
        self.ui_settings.setValue(f"{__name__}/state", state)
        geometry = self.saveGeometry()
        self.ui_settings.setValue(f"{__name__}/geometry", geometry)
        super().closeEvent(a0)

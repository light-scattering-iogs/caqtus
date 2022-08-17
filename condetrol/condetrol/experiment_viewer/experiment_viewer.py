from PyQt5.QtWidgets import QMainWindow

from .experiment_viewer_ui import Ui_MainWindow
from .config_editor import ConfigEditor


class ExperimentViewer(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.action_edit_config.triggered.connect(self.edit_config)

    def edit_config(self):
        editor = ConfigEditor()
        editor.exec()


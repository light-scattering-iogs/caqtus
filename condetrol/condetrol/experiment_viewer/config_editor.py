from PyQt5.QtWidgets import QDialog

from .config_editor_ui import Ui_config_editor

class ConfigEditor(QDialog, Ui_config_editor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
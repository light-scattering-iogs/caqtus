from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog


class SaveGeometryDialog(QDialog):
    def exec(self):
        self._restore_geometry()
        result = super().exec()
        self._save_geometry()
        return result

    def _save_geometry(self):
        ui_settings = QSettings()
        name = self.__class__.__qualname__
        ui_settings.setValue(f"{name}/geometry", self.saveGeometry())

    def _restore_geometry(self):
        ui_settings = QSettings()
        name = self.__class__.__qualname__
        geometry = ui_settings.value(f"{name}/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

from typing import Optional

from PyQt6.QtWidgets import QDialog, QWidget

from analyza.loading.importers import ParametersLoader
from .create_parameters_viewer_ui import Ui_ParametersDialog
from .params_viewer import ParametersViewer


def create_parameters_viewer(
    parent: Optional[QWidget],
) -> Optional[tuple[str, ParametersViewer]]:
    dialog = ViewerDialog(parent)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return (
            dialog.get_title(),
            ParametersViewer(
                importer=ParametersLoader(),
            ),
        )
    return None


class ViewerDialog(QDialog, Ui_ParametersDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)

    def get_title(self) -> str:
        return self._window_title.text()

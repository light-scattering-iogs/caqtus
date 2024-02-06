from typing import Optional

from PySide6.QtWidgets import QDialog, QWidget

from analyza.loading.importers import AtomsLoader2D
from device.name import DeviceName
from image_types import ImageLabel
from .atoms_viewer import AtomsView
from .create_atom_viewer_ui import Ui_AtomDialog


def create_atom_viewer(parent: Optional[QWidget]) -> Optional[tuple[str, AtomsView]]:
    dialog = ViewerDialog(parent)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return (
            dialog.get_title(),
            AtomsView(
                importer=AtomsLoader2D(
                    dialog.get_detector_name(),
                    dialog.get_picture_name(),
                ),
                axes_equal=dialog.get_axes_equal(),
            ),
        )
    return None


class ViewerDialog(QDialog, Ui_AtomDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)

    def get_title(self) -> str:
        return self._window_title.text()

    def get_detector_name(self) -> DeviceName:
        return DeviceName(self._detector_line_edit.text())

    def get_picture_name(self) -> ImageLabel:
        return ImageLabel(self._picture_line_edit.text())

    def get_axes_equal(self) -> bool:
        return self.axesEqualCheckBox.isChecked()

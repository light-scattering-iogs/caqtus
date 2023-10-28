from typing import Optional

from PyQt6.QtWidgets import QDialog, QWidget

from analyza.loading.importers import ImageLoader
from device.name import DeviceName
from image_types import ImageLabel
from viewer.single_shot_viewers import ImageViewer
from .add_image_dialog_ui import Ui_ImageDialog


def create_image_viewer(parent: Optional[QWidget]) -> Optional[tuple[str, ImageViewer]]:
    dialog = ViewerDialog(parent)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return (
            dialog.get_title(),
            ImageViewer(
                importer=ImageLoader(
                    dialog.get_camera_name(),
                    dialog.get_picture_name(),
                ),
            ),
        )
    return None


class ViewerDialog(QDialog, Ui_ImageDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)

    def get_title(self) -> str:
        return self._window_title.text()

    def get_camera_name(self) -> DeviceName:
        return DeviceName(self._camera_line_edit.text())

    def get_picture_name(self) -> ImageLabel:
        return ImageLabel(self._picture_line_edit.text())

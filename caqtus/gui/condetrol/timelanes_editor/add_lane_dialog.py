from collections.abc import Iterable
from typing import Optional

from PySide6.QtWidgets import QDialog, QWidget

from .add_lane_dialog_ui import Ui_AddLaneDialog


class AddLaneDialog(QDialog, Ui_AddLaneDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.setWindowTitle("Add Lane...")

    def get_lane_name(self) -> str:
        return self.lane_name_line_edit.text()

    def get_lane_type(self) -> str:
        return self.lane_type_combobox.currentText()

    def set_lane_types(self, lane_types: Iterable[str]) -> None:
        self.lane_type_combobox.clear()
        self.lane_type_combobox.addItems(lane_types)

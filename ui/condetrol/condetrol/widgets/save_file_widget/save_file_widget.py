from pathlib import Path

from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog


class SaveFileWidget(QWidget):
    file_edited = pyqtSignal(Path)

    def __init__(self, path: Path, caption: str, filter: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._layout = QHBoxLayout()
        self._caption = caption
        self._filter = filter

        self._path = QLineEdit(str(path))
        icon = QtGui.QIcon(":/icons/document-text-open")
        self._button = QPushButton("Open")
        self._button.setIcon(icon)
        self._button.clicked.connect(self.edit_path)
        self._layout.addWidget(self._path)
        self._layout.addWidget(self._button)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self._layout)

    def edit_path(self):
        parent = Path(self._path.text()).parent
        file, ok = QFileDialog.getSaveFileName(
            self, self._caption, str(parent), self._filter
        )
        file = str(Path(file))  # set consistent use of / and \ on windows
        if ok:
            self._path.setText(file)
            self.file_edited.emit(Path(self._path.text()))

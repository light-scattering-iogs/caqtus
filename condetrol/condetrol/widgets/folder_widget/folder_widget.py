import logging
from functools import singledispatchmethod
from pathlib import Path

from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal, QModelIndex, Qt, QAbstractItemModel
from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QAbstractItemDelegate,
)

logger = logging.getLogger(__name__)


class FolderWidget(QWidget):
    folder_edited = pyqtSignal(Path)

    def __init__(self, caption: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._layout = QHBoxLayout()
        self._caption = caption

        self._path = QLineEdit()
        self._path.editingFinished.connect(self._emit_folder_edited)
        icon = QtGui.QIcon(":/icons/folder-open")
        self._button = QPushButton("Open")
        self._button.setIcon(icon)
        self._button.clicked.connect(self.browse_path)
        self._layout.addWidget(self._path)
        self._layout.addWidget(self._button)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self._layout)

    def _emit_folder_edited(self):
        self.folder_edited.emit(Path(self._path.text()))

    def browse_path(self, *_):
        parent = Path(self._path.text()).parent
        directory = QFileDialog.getExistingDirectory(
            self,
            self._caption,
            str(parent),
        )
        if directory:
            self.set_path(directory)
            self._emit_folder_edited()

    def set_path(self, path):
        self._path.setText(str(Path(path)))

    @property
    def path(self):
        return self._path.text()




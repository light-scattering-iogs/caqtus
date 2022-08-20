from functools import singledispatchmethod

from PyQt5.QtCore import QModelIndex, QAbstractItemModel, Qt
from PyQt5.QtWidgets import QAbstractItemDelegate, QWidget

from .folder_widget import FolderWidget


class SettingsDelegate(QAbstractItemDelegate):
    @singledispatchmethod
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        return super().setEditorData(editor, index)

    @setEditorData.register
    def _(self, editor: FolderWidget, index: QModelIndex) -> None:
        path = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        editor.set_path(path)

    @singledispatchmethod
    def setModelData(
        self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex
    ) -> None:
        return super().setModelData(editor, model, index)

    @setModelData.register
    def _(
        self, editor: FolderWidget, model: QAbstractItemModel, index: QModelIndex
    ) -> None:
        model.setData(index, editor.path, Qt.ItemDataRole.EditRole)

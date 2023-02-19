from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtWidgets import QStyledItemDelegate
from .mapping_editor import CalibratedMappingEditor


class MappingDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = CalibratedMappingEditor(parent)
        return editor

    def setEditorData(self, editor: CalibratedMappingEditor, index: QModelIndex):
        mapping = index.model().data(index, Qt.ItemDataRole.EditRole)
        editor.set_unit_mapping(mapping)

    def setModelData(self, editor, model, index):
        pass

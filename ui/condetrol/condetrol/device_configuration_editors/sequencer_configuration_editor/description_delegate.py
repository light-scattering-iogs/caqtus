import logging

from PyQt6.QtCore import QModelIndex, Qt, QAbstractItemModel
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QApplication,
    QStyle,
    QWidget,
    QLineEdit,
)

from core.device.sequencer.configuration import ChannelSpecialPurpose

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ChannelDescriptionDelegate(QStyledItemDelegate):
    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        data = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if isinstance(data, str):
            option.text = data
        elif isinstance(data, ChannelSpecialPurpose):
            if data.is_unused():
                option.text = ""
            else:
                option.text = str(data)
                option.font.setItalic(True)
        QApplication.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem, option, painter
        )

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget:
        return QLineEdit(parent)

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        if not isinstance(editor, QLineEdit):
            raise TypeError("Expected QLineEdit")
        description = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if isinstance(description, str):
            editor.setText(description)
        elif isinstance(description, ChannelSpecialPurpose):
            editor.setText(description.to_yaml())

    def setModelData(
        self,
        editor: QWidget,
        model: QAbstractItemModel,
        index: QModelIndex,
    ) -> None:
        if not isinstance(editor, QLineEdit):
            raise TypeError("Expected QLineEdit")
        text = editor.text()
        try:
            value = SettingsModel.load(text)
        except Exception as e:
            logger.warning(f"Failed to load {text} as YAML: {e}")
        else:
            if isinstance(value, (str, ChannelSpecialPurpose)):
                model.setData(index, value, Qt.ItemDataRole.EditRole)

import logging

from PyQt6.QtCore import QModelIndex, Qt, QAbstractItemModel
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QApplication,
    QStyle,
    QWidget,
    QComboBox,
)

from sequencer.configuration.channel_mapping import (
    OutputMapping,
    DigitalMapping,
    AnalogMapping,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MappingDelegate(QStyledItemDelegate):
    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        mapping: OutputMapping = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if isinstance(mapping, DigitalMapping):
            if mapping.invert:
                option.text = "inverted"
            else:
                option.text = "normal"
        elif isinstance(mapping, AnalogMapping):
            option.text = mapping.format_units()
        QApplication.style().drawControl(
            QStyle.ControlElement.CE_ItemViewItem, option, painter
        )

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget:
        mapping = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if isinstance(mapping, DigitalMapping):
            combobox = QComboBox(parent)
            combobox.addItems(["normal", "inverted"])
            return combobox
        else:
            raise NotImplementedError

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        mapping = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if isinstance(mapping, DigitalMapping):
            combobox: QComboBox = editor  # type: ignore
            if mapping.invert:
                combobox.setCurrentText("inverted")
            else:
                combobox.setCurrentText("normal")
        else:
            raise NotImplementedError

    def setModelData(
        self,
        editor: QWidget,
        model: QAbstractItemModel,
        index: QModelIndex,
    ) -> None:
        mapping = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if isinstance(mapping, DigitalMapping):
            combobox: QComboBox = editor  # type: ignore
            if combobox.currentText() == "inverted":
                mapping.invert = True
            elif combobox.currentText() == "normal":
                mapping.invert = False
            else:
                raise ValueError(f"Unknown mapping value: {combobox.currentText()}")
            index.model().setData(index, mapping, Qt.ItemDataRole.EditRole)
        else:
            raise NotImplementedError

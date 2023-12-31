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

from core.device.sequencer.configuration import (
    OutputMapping,
    DigitalMapping,
    CalibratedAnalogMapping,
)
from .mapping_editor import CalibratedMappingEditor

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
        elif isinstance(mapping, CalibratedAnalogMapping):
            option.text = mapping.format_units()
        else:
            raise NotImplementedError(
                f"Don't know how to paint mapping type {type(mapping)}"
            )
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
        elif isinstance(mapping, CalibratedAnalogMapping):
            input_label = index.model().data(
                index.model().index(index.row(), 0), Qt.ItemDataRole.DisplayRole
            )
            editor = CalibratedMappingEditor(input_label, "Output voltages", parent)
            return editor
        else:
            raise NotImplementedError(
                f"Don't know how to create editor for {type(mapping)}"
            )

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        mapping = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if isinstance(mapping, DigitalMapping):
            combobox: QComboBox = editor  # type: ignore
            if mapping.invert:
                combobox.setCurrentText("inverted")
            else:
                combobox.setCurrentText("normal")
        elif isinstance(mapping, CalibratedAnalogMapping):
            mapping_editor: CalibratedMappingEditor = editor  # type: ignore
            mapping_editor.set_unit_mapping(mapping)
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
        elif isinstance(mapping, CalibratedAnalogMapping):
            mapping_editor: CalibratedMappingEditor = editor  # type: ignore
            index.model().setData(
                index, mapping_editor.get_mapping(), Qt.ItemDataRole.EditRole
            )
        else:
            raise NotImplementedError

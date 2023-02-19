from PyQt6 import QtCore
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QPainter, QColor, QBrush
from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QWidget,
    QColorDialog,
)
from pydantic.color import Color


class ColorCellDelegate(QStyledItemDelegate):
    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        # noinspection PyTypeChecker
        model = index.model()
        color = model.data(index, Qt.ItemDataRole.DisplayRole)
        super().paint(painter, option, index)
        if isinstance(color, Color):
            color = color.as_rgb_tuple(alpha=True)
            color = color[0:3] + (int(color[3] * 255),)
            brush = QBrush(QColor.fromRgb(*color))
            painter.fillRect(option.rect, brush)
            if option.state & QStyle.StateFlag.State_Selected:
                c = option.palette.highlight().color()
                c.setAlphaF(0.8)
                brush = QBrush(c)
                painter.fillRect(option.rect, brush)

    def createEditor(
        self, parent: QWidget, option: "QStyleOptionViewItem", index: QtCore.QModelIndex
    ) -> QWidget:
        widget = QColorDialog(parent)
        widget.setOption(QColorDialog.ColorDialogOption.NoButtons, True)
        widget.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        return widget

    def setEditorData(self, editor: QColorDialog, index: QtCore.QModelIndex) -> None:
        color = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if color is not None:
            color = color.as_rgb_tuple(alpha=True)
            color = color[0:3] + (int(color[3] * 255),)
            editor.setCurrentColor(QColor.fromRgb(*color))

    def setModelData(
        self,
        editor: QColorDialog,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ) -> None:
        color = editor.currentColor().getRgb()
        color = Color(color[0:3] + (color[3] / 255,))
        model.setData(index, color, Qt.ItemDataRole.EditRole)

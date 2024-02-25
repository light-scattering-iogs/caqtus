from typing import Optional

from PySide6 import QtWidgets
from PySide6.QtCore import QSize, QModelIndex, Qt, QRectF
from PySide6.QtGui import QTextDocument, QAbstractTextDocumentLayout
from PySide6.QtWidgets import (
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)


class HTMLItemDelegate(QStyledItemDelegate):
    """A delegate that can renders HTML when painting items in a view."""

    def __init__(self, parent: Optional[QWidget] = None):
        self.doc = QTextDocument()
        super().__init__(parent)

    def get_text_to_render(self, index: QModelIndex) -> str:
        """Return the text to render in the delegate.

        Override this method to customize the rendering of the text.
        """

        return str(index.data(role=Qt.DisplayRole))

    def paint(self, painter, option, index):
        options = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        painter.save()
        self.doc.setTextWidth(options.rect.width())
        text = self.get_text_to_render(index)
        self.doc.setHtml(text)
        self.doc.setDefaultFont(options.font)
        options.text = ""
        options.widget.style().drawControl(
            QtWidgets.QStyle.ControlElement.CE_ItemViewItem, options, painter
        )
        painter.translate(options.rect.left(), options.rect.top())
        clip = QRectF(0, 0, options.rect.width(), options.rect.height())
        painter.setClipRect(clip)
        ctx = QAbstractTextDocumentLayout.PaintContext()
        ctx.clip = clip
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())

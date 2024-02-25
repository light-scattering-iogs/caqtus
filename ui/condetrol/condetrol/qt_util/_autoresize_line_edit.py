from PySide6.QtCore import QSize
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QLineEdit, QStyleOptionFrame, QStyle


class AutoResizeLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.resize_to_content)

    def _resize_to_content(self):
        font_metric = QFontMetrics(self.font())
        pixel_width = font_metric.width(self.text())
        self.setFixedWidth(pixel_width)
        self.adjustSize()

    def resize_to_content(self):
        text = self.text()
        text_size = self.fontMetrics().size(0, text)
        tm = self.textMargins()
        tm_size = QSize(tm.left() + tm.right(), tm.top() + tm.bottom())
        cm = self.contentsMargins()
        cm_size = QSize(cm.left() + cm.right(), cm.top() + cm.bottom())
        extra_size = QSize(8, 4)
        contents_size = text_size + tm_size + cm_size + extra_size
        op = QStyleOptionFrame()
        op.initFrom(self)
        perfect_size = self.style().sizeFromContents(
            QStyle.ContentsType.CT_LineEdit, op, contents_size
        )
        self.setFixedSize(perfect_size)

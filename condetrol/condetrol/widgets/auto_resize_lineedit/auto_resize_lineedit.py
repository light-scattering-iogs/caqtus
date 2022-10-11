import logging

from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QLineEdit

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class AutoResizeLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.resize_to_content)

    def resize_to_content(self):
        font_metric = QFontMetrics(self.font())
        pixel_width = font_metric.width(self.text() + " " * 2)
        self.setFixedWidth(pixel_width)
        self.adjustSize()



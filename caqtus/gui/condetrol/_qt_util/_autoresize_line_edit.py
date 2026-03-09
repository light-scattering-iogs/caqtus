from PySide6.QtCore import QSize
from PySide6.QtWidgets import QLineEdit, QStyleOptionFrame, QStyle


class AutoResizeLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.textChanged.connect(self.resize_to_content)

    def resize_to_content(self):
        text = self.get_text()
        self.resize_to_text(text)

    def get_text(self):
        completer = self.completer()
        if completer is not None:
            if completer.popup().isVisible():
                model = completer.completionModel()
                if model.rowCount() > 0:
                    longest_suggestion = max(
                        (
                            model.data(model.index(index, 0))
                            for index in range(model.rowCount())
                        ),
                        key=lambda x: len(x),
                    )
                    return longest_suggestion
        text = self.text()
        if text:
            return text
        else:
            return self.placeholderText()

    def setCompleter(self, completer):
        super().setCompleter(completer)
        if completer is not None:
            completer.highlighted.connect(self.resize_to_text)

    def resize_to_text(self, text):
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

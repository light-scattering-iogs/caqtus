from PyQt6.QtWidgets import QDialog
from exception_tree import create_exception_tree

from .exception_dialog_ui import Ui_ExceptionDialog


class ExceptionDialog(QDialog, Ui_ExceptionDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

    def set_exception(self, exception: BaseException):
        self.exception_tree.setColumnCount(2)
        tree = create_exception_tree(exception)

        self.exception_tree.addTopLevelItems(tree)
        self.exception_tree.expandAll()
        self.exception_tree.resizeColumnToContents(0)
        self.exception_tree.resizeColumnToContents(1)
        self.setWindowTitle("Error")

    def set_message(self, message: str):
        self.exception_label.setText(message)

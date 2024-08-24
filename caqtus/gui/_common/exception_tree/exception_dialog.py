from PySide6.QtWidgets import QDialog

from caqtus.session import TracebackSummary
from ._exception_tree import create_exception_tree
from .exception_dialog_ui import Ui_ExceptionDialog
from ...qtutil import HTMLItemDelegate


class ExceptionDialog(QDialog, Ui_ExceptionDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.exception_tree.setItemDelegateForColumn(2, HTMLItemDelegate(self))

    def set_exception(self, tb_summary: TracebackSummary):
        self.exception_tree.setColumnCount(3)
        tree = create_exception_tree(tb_summary)

        self.exception_tree.addTopLevelItems(tree)
        self.exception_tree.expandAll()
        for column in range(self.exception_tree.columnCount()):
            self.exception_tree.resizeColumnToContents(column)
        self.setWindowTitle("Error")

    def set_message(self, message: str):
        self.exception_label.setText(message)

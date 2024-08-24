from typing import Optional

from PySide6 import QtWidgets

from caqtus.session import TracebackSummary
from ._exception_tree import create_exception_tree
from .exception_dialog_ui import Ui_ExceptionDialog
from ...qtutil import HTMLItemDelegate


class ExceptionDialog(QtWidgets.QDialog, Ui_ExceptionDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.exception_tree.setItemDelegateForColumn(2, HTMLItemDelegate(self))
        self.exception_tree.setColumnCount(3)

    def set_exception(self, tb_summary: Optional[TracebackSummary]):
        self.exception_tree.clear()
        if tb_summary:
            tree = create_exception_tree(tb_summary)
            self.exception_tree.addTopLevelItems(tree)
        self.exception_tree.expandAll()
        for column in range(self.exception_tree.columnCount()):
            self.exception_tree.resizeColumnToContents(column)
        self.exception_tree.hideColumn(1)
        self.setWindowTitle("Error")

    def set_message(self, message: str):
        self.exception_label.setText(message)

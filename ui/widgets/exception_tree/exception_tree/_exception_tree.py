from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QTreeWidgetItem, QApplication


def create_exception_tree(
    exception: BaseException, prepend: str = "Error:"
) -> list[QTreeWidgetItem]:
    result = []
    exception_item = QTreeWidgetItem(None, [prepend, str(exception)])
    highlight_color = QApplication.palette().color(QPalette.ColorRole.Accent)
    exception_item.setForeground(0, highlight_color)
    result.append(exception_item)
    if isinstance(exception, ExceptionGroup):
        for child_exception in exception.exceptions:
            exception_item.addChildren(create_exception_tree(child_exception, "Child:"))
    if exception.__cause__ is not None:
        for cause in create_exception_tree(exception.__cause__, "Cause:"):
            exception_item.addChild(cause)
    return result

from PySide6.QtGui import Qt, QPalette
from PySide6.QtWidgets import QTreeWidgetItem, QApplication


def create_exception_tree(
    exception: BaseException, prepend: str = "error:"
) -> list[QTreeWidgetItem]:
    result = []
    text = str(exception)
    if isinstance(exception, ExceptionGroup):
        text = exception.args[0]
    exception_label = type(exception).__name__
    exception_item = QTreeWidgetItem(None, [prepend, exception_label, text])
    error_color = Qt.GlobalColor.red
    highlight_color = QApplication.palette().color(QPalette.ColorRole.Accent)
    exception_item.setForeground(0, highlight_color)
    exception_item.setForeground(1, error_color)
    exception_item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)
    result.append(exception_item)
    if hasattr(exception, "__notes__"):
        for note in exception.__notes__:
            note_item = QTreeWidgetItem(exception_item, ["", "", note])
            exception_item.addChild(note_item)
    if isinstance(exception, ExceptionGroup):
        for i, child_exception in enumerate(exception.exceptions):
            exception_item.addChildren(
                create_exception_tree(child_exception, f"Sub-error {i}")
            )
    if exception.__cause__ is not None:
        for cause in create_exception_tree(exception.__cause__, "because:"):
            exception_item.addChild(cause)
    return result

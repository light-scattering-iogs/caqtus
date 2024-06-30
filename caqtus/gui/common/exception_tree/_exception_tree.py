import re

from PySide6.QtGui import Qt, QPalette
from PySide6.QtWidgets import QTreeWidgetItem, QApplication


def create_exception_tree(
    exception: BaseException, prepend: str = "error:"
) -> list[QTreeWidgetItem]:
    result = []
    text = str(exception)
    if isinstance(exception, ExceptionGroup):
        text = exception.args[0]
    text = process_text(text)
    exception_label = type(exception).__name__
    exception_item = QTreeWidgetItem(None, [prepend, exception_label, text])
    error_color = Qt.GlobalColor.red
    highlight_color = QApplication.palette().color(QPalette.ColorRole.Accent)
    exception_item.setForeground(0, highlight_color)
    exception_item.setForeground(1, error_color)
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


def process_text(text: str) -> str:
    color = QApplication.palette().color(QPalette.ColorRole.Accent).name()
    text = highlight_device_name(text, color)
    text = highlight_device_servers(text, color)
    text = highlight_expression(text, color)
    text = highlight_parameter(text, color)
    text = highlight_type(text, color)
    text = highlight_step(text, color)

    return text


def highlight_device_name(value: str, color) -> str:
    def replace(match):
        return f'device <b><font color="{color}">{match.group(1)}</font></b>'

    return re.sub(r"device '(.+?)'", replace, value)


def highlight_device_servers(text: str, color) -> str:
    def replace(match):
        return f'device server <b><font color="{color}">{match.group(1)}</font></b>'

    return re.sub(r"device server '(.+?)'", replace, text)


def highlight_expression(text: str, color) -> str:
    def replace(match):
        return f'expression <b><font color="{color}">{match.group(1)}</font></b>'

    return re.sub(r"expression '(.+?)'", replace, text)


def highlight_parameter(text: str, color) -> str:
    def replace(match):
        return f'parameter <b><font color="{color}">{match.group(1)}</font></b>'

    return re.sub(r"parameter '(.+?)'", replace, text)


def highlight_type(text: str, color) -> str:
    def replace(match):
        return f'type <b><font color="{color}">{match.group(1)}</font></b>'

    return re.sub(r"type '(.+?)'", replace, text)


def highlight_step(text: str, color) -> str:
    def replace(match):
        return f'step <b><font color="{color}">{match.group(1)} (<i>{match.group(2)}</i>)</font></b>'

    return re.sub(r"step ([0-9]+) \((.+?)\)", replace, text)

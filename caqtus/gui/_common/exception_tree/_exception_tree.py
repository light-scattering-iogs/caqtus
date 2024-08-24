import re

from PySide6.QtGui import Qt, QPalette
from PySide6.QtWidgets import QTreeWidgetItem, QApplication

from caqtus.session import TracebackSummary


def create_exception_tree(
    tb_summary: TracebackSummary, prepend: str = "error:"
) -> list[QTreeWidgetItem]:
    result = []
    text = tb_summary.exc_msg
    text = process_text(text)
    exception_label = tb_summary.exc_type
    exception_item = QTreeWidgetItem(None, [prepend, exception_label, text])  # type: ignore
    error_color = Qt.GlobalColor.red
    highlight_color = QApplication.palette().color(QPalette.ColorRole.Accent)
    exception_item.setForeground(0, highlight_color)
    exception_item.setForeground(1, error_color)
    result.append(exception_item)
    if tb_summary.notes:
        for note in tb_summary.notes:
            note_item = QTreeWidgetItem(exception_item, ["", "", note])
            exception_item.addChild(note_item)
    if tb_summary.exceptions:
        for i, child_exception in enumerate(tb_summary.exceptions):
            exception_item.addChildren(
                create_exception_tree(child_exception, f"Sub-error {i}")
            )
    if tb_summary.cause:
        for cause in create_exception_tree(tb_summary.cause, "because:"):
            exception_item.addChild(cause)
    return result


def process_text(text: str) -> str:
    color = QApplication.palette().color(QPalette.ColorRole.Accent).name()
    text = highlight_device_name(text, color)
    text = highlight_device_servers(text, color)
    text = highlight_expression(text, color)
    # device parameter must be highlighted before parameter, because they match the
    # same pattern
    text = hightlight_device_parameter(text, color)
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


def hightlight_device_parameter(text: str, color) -> str:
    def replace(match):
        return f'device parameter <b><font color="{color}">{match.group(1)} = {match.group(2)}</font></b>'

    return re.sub(r"device parameter '(.+?)' = '(.+?)'", replace, text)

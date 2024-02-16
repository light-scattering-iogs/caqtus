import functools

import qtawesome
from PySide6.QtGui import QIcon


def get_icon(name: str, color) -> QIcon:
    ids = {
        "camera": "mdi6.camera-outline",
        "editable-sequence": "mdi6.pencil-outline",
        "read-only-sequence": "mdi6.pencil-off-outline",
    }

    icon = qtawesome.icon(ids[name], color=color)
    return icon

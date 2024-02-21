import functools

import qtawesome
from PySide6.QtGui import QIcon


def get_icon(name: str, color) -> QIcon:
    ids = {
        "camera": "mdi6.camera-outline",
        "editable-sequence": "mdi6.pencil-outline",
        "read-only-sequence": "mdi6.pencil-off-outline",
        "start": "mdi6.play",
        "stop": "mdi6.stop",
        "delete": "mdi6.delete",
        "duplicate": "mdi6.content-duplicate",
        "clear": "mdi6.database-remove",
        "plus": "mdi6.plus",
        "minus": "mdi6.minus",
        "copy": "mdi6.content-copy",
        "paste": "mdi6.content-paste",
    }

    icon = qtawesome.icon(ids[name], color=color)
    return icon

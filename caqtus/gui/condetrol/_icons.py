import qtawesome
from PySide6.QtGui import QIcon, QPalette


def get_icon(name: str, color=None) -> QIcon:
    """Get an icon by name.

    Args:
        name: The name of the icon.
        color: The color of the icon. If None, the default color is used.
    """

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
        "simplify-timelanes": "mdi6.table-merge-cells",
        "add-time-lane": "mdi6.table-row-plus-after",
    }
    if color is None:
        color = QPalette().buttonText().color()
    if name in ids:
        name = ids[name]
    icon = qtawesome.icon(name, color=color)
    return icon

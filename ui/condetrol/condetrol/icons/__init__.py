import functools
from pathlib import Path

from PySide6.QtGui import QIcon


@functools.lru_cache(maxsize=None)
def get_icon(name: str) -> QIcon:
    if name == "camera":
        return QIcon(str(Path(__file__).parent / "camera-lens.png"))
    else:
        raise ValueError(f"Unknown icon name: {name}")

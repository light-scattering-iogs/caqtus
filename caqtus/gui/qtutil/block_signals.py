import contextlib
from collections.abc import Generator

from PySide6.QtCore import QObject


@contextlib.contextmanager
def block_signals(obj: QObject) -> Generator[None, None, None]:
    """Context manager to block signals from a QObject."""

    obj.blockSignals(True)
    yield
    obj.blockSignals(False)

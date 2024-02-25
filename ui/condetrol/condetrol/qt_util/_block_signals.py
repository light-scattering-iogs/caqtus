import contextlib

from PySide6.QtCore import QObject


@contextlib.contextmanager
def block_signals(obj: QObject) -> None:
    """Context manager to block signals from a QObject."""

    obj.blockSignals(True)
    yield
    obj.blockSignals(False)

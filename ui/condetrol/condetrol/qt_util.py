import contextlib

from PySide6.QtCore import QObject


@contextlib.contextmanager
def block_signals(obj: QObject) -> None:
    obj.blockSignals(True)
    yield
    obj.blockSignals(False)

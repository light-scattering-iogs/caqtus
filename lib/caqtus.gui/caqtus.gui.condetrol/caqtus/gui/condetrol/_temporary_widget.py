import contextlib
from typing import TypeVar

from PySide6.QtWidgets import QWidget

T = TypeVar("T", bound=QWidget)


class temporary_widget(contextlib.AbstractContextManager[T]):
    def __init__(self, widget: T) -> None:
        self.widget = widget

    def __enter__(self) -> T:
        return self.widget

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.widget.deleteLater()

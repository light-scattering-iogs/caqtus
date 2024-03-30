import contextlib
from typing import TypeVar

from PySide6.QtWidgets import QWidget

T = TypeVar("T", bound=QWidget)


@contextlib.contextmanager
def temporary_widget(widget: T) -> T:
    """Context manager that deletes a widget when the context is exited.

    When a widget is created for a lifetime shorter than the lifetime of its parent,
    it is necessary to delete it manually to avoid memory leaks.
    This is easily forgotten, so this context manager can be used to ensure that
    the widget is deleted when it is no longer needed.

    Example:

        .. code-block:: python

                with temporary_widget(QWidget(parent=parent)) as widget:
                    widget.show()
                    widget.do_something()
    """

    try:
        yield widget
    finally:
        widget.deleteLater()
